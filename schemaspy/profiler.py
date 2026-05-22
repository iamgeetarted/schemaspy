"""Data profiling for SQLite tables: null counts, distinct counts, min/max, samples."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from schemaspy.models import TableInfo


@dataclass
class ColumnProfile:
    table_name: str
    col_name: str
    col_type: str
    row_count: int
    null_count: int
    null_pct: float
    distinct_count: int
    min_val: str | None
    max_val: str | None
    sample_vals: list[str] = field(default_factory=list)


def profile_table(db_path: str, table: TableInfo) -> list[ColumnProfile]:
    """Profile every column in *table*, returning one ColumnProfile per column."""
    profiles: list[ColumnProfile] = []
    con = sqlite3.connect(db_path)
    try:
        # Total row count for the table
        cur = con.execute(f"SELECT COUNT(*) FROM [{table.name}]")
        row_count: int = cur.fetchone()[0]

        for col in table.columns:
            t = table.name
            c = col.name

            # Null count via arithmetic: COUNT(*) - COUNT(col) counts NULLs
            cur = con.execute(
                f"SELECT COUNT(*) - COUNT([{c}]) FROM [{t}]"
            )
            null_count: int = cur.fetchone()[0]

            null_pct: float = (null_count / row_count * 100.0) if row_count > 0 else 0.0

            # Distinct count
            cur = con.execute(f"SELECT COUNT(DISTINCT [{c}]) FROM [{t}]")
            distinct_count: int = cur.fetchone()[0]

            # Min / max as text (CAST handles all SQLite types uniformly)
            cur = con.execute(
                f"SELECT MIN(CAST([{c}] AS TEXT)), MAX(CAST([{c}] AS TEXT)) FROM [{t}]"
            )
            row = cur.fetchone()
            min_val: str | None = row[0]
            max_val: str | None = row[1]

            # Up to 5 non-null sample values
            cur = con.execute(
                f"SELECT CAST([{c}] AS TEXT) FROM [{t}] WHERE [{c}] IS NOT NULL LIMIT 5"
            )
            sample_vals: list[str] = [r[0] for r in cur.fetchall() if r[0] is not None]

            profiles.append(
                ColumnProfile(
                    table_name=t,
                    col_name=c,
                    col_type=col.type,
                    row_count=row_count,
                    null_count=null_count,
                    null_pct=null_pct,
                    distinct_count=distinct_count,
                    min_val=min_val,
                    max_val=max_val,
                    sample_vals=sample_vals,
                )
            )
    finally:
        con.close()

    return profiles


def profile_database(
    db_path: str, tables: list[TableInfo]
) -> dict[str, list[ColumnProfile]]:
    """Profile all tables and return a mapping of table name → list of ColumnProfile."""
    result: dict[str, list[ColumnProfile]] = {}
    for table in tables:
        result[table.name] = profile_table(db_path, table)
    return result
