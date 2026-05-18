"""Data models for schemaspy schema analysis."""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ColumnInfo:
    name: str
    type: str
    nullable: bool
    primary_key: bool
    default: str | None = None


@dataclass
class IndexInfo:
    name: str
    columns: list[str]
    unique: bool


@dataclass
class ForeignKey:
    column: str
    ref_table: str
    ref_column: str


@dataclass
class TableInfo:
    name: str
    columns: list[ColumnInfo] = field(default_factory=list)
    indexes: list[IndexInfo] = field(default_factory=list)
    foreign_keys: list[ForeignKey] = field(default_factory=list)
    row_count: int = 0
    ai_doc: str = ""


@dataclass
class SchemaIssue:
    severity: str  # "warning" | "info"
    table: str
    message: str


@dataclass
class SchemaReport:
    db_path: str
    tables: list[TableInfo] = field(default_factory=list)
    issues: list[SchemaIssue] = field(default_factory=list)
    generated_at: str = ""
