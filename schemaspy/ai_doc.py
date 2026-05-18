"""Claude streaming documentation generator for schema tables and issues."""

from __future__ import annotations

from schemaspy.models import SchemaIssue, TableInfo


def stream_table_doc(table: TableInfo, client: object) -> str:
    """Stream a documentation paragraph for a table. Returns full text."""
    schema_text = f"Table: {table.name}\nColumns: " + ", ".join(
        f"{c.name} ({c.type}{'?' if c.nullable else ''})" for c in table.columns
    )
    if table.foreign_keys:
        schema_text += "\nForeign keys: " + ", ".join(
            f"{fk.column}→{fk.ref_table}.{fk.ref_column}" for fk in table.foreign_keys
        )
    schema_text += f"\nRow count: {table.row_count}"

    prompt = (
        f"{schema_text}\n\n"
        "Write a concise 2-3 sentence description of what this table likely stores "
        "and its role in the schema. Be specific about the data model."
    )

    full_text = ""
    with client.messages.stream(  # type: ignore[attr-defined]
        model="claude-haiku-4-5-20251001",
        max_tokens=150,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for chunk in stream.text_stream:
            full_text += chunk
    return full_text.strip()


def stream_issues_doc(issues: list[SchemaIssue], client: object) -> str:
    """Stream an AI summary of detected schema issues."""
    if not issues:
        return "No issues detected."

    issue_text = "\n".join(
        f"- [{i.severity.upper()}] {i.table}: {i.message}" for i in issues
    )
    prompt = (
        f"Schema issues found:\n{issue_text}\n\n"
        "Briefly explain the impact of these issues and prioritize which to fix first (2-4 sentences)."
    )

    full_text = ""
    with client.messages.stream(  # type: ignore[attr-defined]
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for chunk in stream.text_stream:
            full_text += chunk
    return full_text.strip()
