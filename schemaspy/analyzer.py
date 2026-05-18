"""SQLite schema analysis using stdlib sqlite3."""

from __future__ import annotations

import asyncio
import sqlite3
from datetime import datetime, timezone

from schemaspy.models import (
    ColumnInfo,
    ForeignKey,
    IndexInfo,
    SchemaIssue,
    SchemaReport,
    TableInfo,
)


def _get_table_names(db_path: str) -> list[str]:
    """Return all user-defined table names in the database."""
    con = sqlite3.connect(db_path)
    try:
        cur = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        return [row[0] for row in cur.fetchall()]
    finally:
        con.close()


def _analyze_table(db_path: str, table_name: str) -> TableInfo:
    """Analyze a single table and return its TableInfo."""
    con = sqlite3.connect(db_path)
    try:
        # Columns
        columns: list[ColumnInfo] = []
        cur = con.execute(f"PRAGMA table_info({table_name})")
        for row in cur.fetchall():
            # cid, name, type, notnull, dflt_value, pk
            columns.append(
                ColumnInfo(
                    name=row[1],
                    type=row[2] or "TEXT",
                    nullable=not bool(row[3]),
                    primary_key=bool(row[5]),
                    default=row[4],
                )
            )

        # Indexes
        indexes: list[IndexInfo] = []
        cur = con.execute(f"PRAGMA index_list({table_name})")
        for idx_row in cur.fetchall():
            # seq, name, unique, origin, partial
            idx_name = idx_row[1]
            idx_unique = bool(idx_row[2])
            idx_cur = con.execute(f"PRAGMA index_info({idx_name})")
            idx_columns = [r[2] for r in idx_cur.fetchall()]
            indexes.append(IndexInfo(name=idx_name, columns=idx_columns, unique=idx_unique))

        # Foreign keys
        foreign_keys: list[ForeignKey] = []
        cur = con.execute(f"PRAGMA foreign_key_list({table_name})")
        for fk_row in cur.fetchall():
            # id, seq, table, from, to, on_update, on_delete, match
            foreign_keys.append(
                ForeignKey(
                    column=fk_row[3],
                    ref_table=fk_row[2],
                    ref_column=fk_row[4],
                )
            )

        # Row count
        cur = con.execute(f"SELECT COUNT(*) FROM [{table_name}]")
        row_count: int = cur.fetchone()[0]

        return TableInfo(
            name=table_name,
            columns=columns,
            indexes=indexes,
            foreign_keys=foreign_keys,
            row_count=row_count,
        )
    finally:
        con.close()


def _detect_issues(tables: list[TableInfo]) -> list[SchemaIssue]:
    """Detect common schema issues across all tables."""
    issues: list[SchemaIssue] = []

    for table in tables:
        # Collect all indexed columns for this table
        indexed_cols: set[str] = set()
        for idx in table.indexes:
            for col in idx.columns:
                indexed_cols.add(col)

        # Also treat primary key columns as indexed
        for col in table.columns:
            if col.primary_key:
                indexed_cols.add(col.name)

        # Issue: FK columns with no index
        for fk in table.foreign_keys:
            if fk.column not in indexed_cols:
                issues.append(
                    SchemaIssue(
                        severity="warning",
                        table=table.name,
                        message=f"Foreign key column '{fk.column}' referencing {fk.ref_table}.{fk.ref_column} has no index",
                    )
                )

        # Issue: table has no primary key
        has_pk = any(col.primary_key for col in table.columns)
        if not has_pk:
            issues.append(
                SchemaIssue(
                    severity="warning",
                    table=table.name,
                    message="Table has no primary key column",
                )
            )

        # Issue: empty table
        if table.row_count == 0:
            issues.append(
                SchemaIssue(
                    severity="info",
                    table=table.name,
                    message="Table has no rows",
                )
            )

    return issues


def analyze_schema(db_path: str) -> SchemaReport:
    """Synchronously analyze the full schema of a SQLite database."""
    table_names = _get_table_names(db_path)
    tables: list[TableInfo] = []
    for name in table_names:
        tables.append(_analyze_table(db_path, name))

    report = SchemaReport(
        db_path=db_path,
        tables=tables,
        issues=_detect_issues(tables),
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    return report


async def async_analyze_schema(db_path: str) -> SchemaReport:
    """Asynchronously analyze the full schema using asyncio.TaskGroup for concurrency."""
    table_names = _get_table_names(db_path)

    tasks: list[asyncio.Task[TableInfo]] = []
    async with asyncio.TaskGroup() as tg:
        for name in table_names:
            tasks.append(tg.create_task(asyncio.to_thread(_analyze_table, db_path, name)))

    tables = [t.result() for t in tasks]

    report = SchemaReport(
        db_path=db_path,
        tables=tables,
        issues=_detect_issues(tables),
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    return report
