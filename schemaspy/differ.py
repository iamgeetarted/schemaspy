"""Schema diff: compare two SchemaReport objects and surface structural changes."""

from __future__ import annotations

from dataclasses import dataclass, field

from schemaspy.models import SchemaReport


@dataclass
class TableChanges:
    added_columns: list[str] = field(default_factory=list)
    removed_columns: list[str] = field(default_factory=list)
    # column name → (old_type, new_type)
    type_changes: dict[str, tuple[str, str]] = field(default_factory=dict)


@dataclass
class SchemaDiff:
    added_tables: list[str] = field(default_factory=list)
    removed_tables: list[str] = field(default_factory=list)
    # table name → changes (only present when the table exists in both reports)
    changed_tables: dict[str, TableChanges] = field(default_factory=dict)

    @property
    def has_changes(self) -> bool:
        """Return True if there is at least one difference."""
        if self.added_tables or self.removed_tables:
            return True
        return any(
            (tc.added_columns or tc.removed_columns or tc.type_changes)
            for tc in self.changed_tables.values()
        )


def diff_schemas(old_report: SchemaReport, new_report: SchemaReport) -> SchemaDiff:
    """Compare *old_report* against *new_report* and return a SchemaDiff."""
    old_tables: dict[str, dict[str, str]] = {
        t.name: {c.name: c.type for c in t.columns} for t in old_report.tables
    }
    new_tables: dict[str, dict[str, str]] = {
        t.name: {c.name: c.type for c in t.columns} for t in new_report.tables
    }

    old_names = set(old_tables)
    new_names = set(new_tables)

    added_tables = sorted(new_names - old_names)
    removed_tables = sorted(old_names - new_names)
    changed_tables: dict[str, TableChanges] = {}

    for table_name in sorted(old_names & new_names):
        old_cols = old_tables[table_name]
        new_cols = new_tables[table_name]

        old_col_names = set(old_cols)
        new_col_names = set(new_cols)

        added_columns = sorted(new_col_names - old_col_names)
        removed_columns = sorted(old_col_names - new_col_names)
        type_changes: dict[str, tuple[str, str]] = {}

        for col in sorted(old_col_names & new_col_names):
            if old_cols[col] != new_cols[col]:
                type_changes[col] = (old_cols[col], new_cols[col])

        if added_columns or removed_columns or type_changes:
            changed_tables[table_name] = TableChanges(
                added_columns=added_columns,
                removed_columns=removed_columns,
                type_changes=type_changes,
            )

    return SchemaDiff(
        added_tables=added_tables,
        removed_tables=removed_tables,
        changed_tables=changed_tables,
    )
