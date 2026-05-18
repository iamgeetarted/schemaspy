"""Tests for schemaspy.exporter (JSON, Markdown, HTML)."""

import json

from schemaspy.exporter import export_html, export_json, export_markdown
from schemaspy.models import ColumnInfo, SchemaIssue, SchemaReport, TableInfo


def _sample_report() -> SchemaReport:
    return SchemaReport(
        db_path="test.db",
        tables=[
            TableInfo(
                name="users",
                columns=[
                    ColumnInfo("id", "INTEGER", False, True),
                    ColumnInfo("name", "TEXT", False, False),
                ],
                row_count=5,
            )
        ],
        issues=[SchemaIssue(severity="warning", table="users", message="No index on FK column")],
        generated_at="2026-05-18T00:00:00",
    )


def test_export_json() -> None:
    report = _sample_report()
    out = export_json(report)
    data = json.loads(out)
    assert data["db_path"] == "test.db"
    assert len(data["tables"]) == 1
    assert data["tables"][0]["name"] == "users"


def test_export_json_has_issues() -> None:
    report = _sample_report()
    data = json.loads(export_json(report))
    assert len(data["issues"]) == 1
    assert data["issues"][0]["severity"] == "warning"


def test_export_json_columns() -> None:
    report = _sample_report()
    data = json.loads(export_json(report))
    cols = data["tables"][0]["columns"]
    assert any(c["name"] == "id" for c in cols)


def test_export_markdown() -> None:
    report = _sample_report()
    out = export_markdown(report)
    assert "# Schema Report" in out
    assert "users" in out
    assert "warning" in out.lower()


def test_export_markdown_db_path() -> None:
    report = _sample_report()
    out = export_markdown(report)
    assert "test.db" in out


def test_export_markdown_column_table() -> None:
    report = _sample_report()
    out = export_markdown(report)
    assert "| Name |" in out
    assert "id" in out


def test_export_html() -> None:
    report = _sample_report()
    out = export_html(report)
    assert "<!DOCTYPE html>" in out
    assert "users" in out


def test_export_html_dark_theme() -> None:
    report = _sample_report()
    out = export_html(report)
    # Check for dark background colour
    assert "#0d1117" in out


def test_export_html_issue_badge() -> None:
    report = _sample_report()
    out = export_html(report)
    assert "WARNING" in out


def test_export_html_row_count() -> None:
    report = _sample_report()
    out = export_html(report)
    assert "5 rows" in out


def test_export_json_round_trip() -> None:
    report = _sample_report()
    data = json.loads(export_json(report))
    assert data["generated_at"] == "2026-05-18T00:00:00"
