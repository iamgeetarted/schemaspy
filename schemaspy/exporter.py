"""Export SchemaReport to Markdown, JSON, or HTML."""

from __future__ import annotations

import dataclasses
import json

from schemaspy.models import SchemaReport


def _dataclass_to_dict(obj: object) -> object:
    """Recursively convert dataclasses to dicts for JSON serialization."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _dataclass_to_dict(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, list):
        return [_dataclass_to_dict(item) for item in obj]
    return obj


def export_json(report: SchemaReport) -> str:
    """Serialize the SchemaReport to a JSON string."""
    return json.dumps(_dataclass_to_dict(report), indent=2)


def export_markdown(report: SchemaReport) -> str:
    """Render the SchemaReport as Markdown."""
    lines: list[str] = []
    lines.append("# Schema Report")
    lines.append("")
    lines.append(f"**Database:** `{report.db_path}`")
    lines.append(f"**Generated:** {report.generated_at}")
    lines.append(f"**Tables:** {len(report.tables)}")
    lines.append("")

    if report.issues:
        lines.append("## Issues")
        lines.append("")
        for issue in report.issues:
            badge = "⚠️" if issue.severity == "warning" else "ℹ️"
            lines.append(f"- {badge} **[{issue.severity.upper()}]** `{issue.table}`: {issue.message}")
        lines.append("")

    lines.append("## Tables")
    lines.append("")

    for table in report.tables:
        lines.append(f"### `{table.name}`")
        lines.append("")
        lines.append(f"**Row count:** {table.row_count}")
        lines.append("")

        if table.ai_doc:
            lines.append(f"> {table.ai_doc}")
            lines.append("")

        lines.append("**Columns:**")
        lines.append("")
        lines.append("| Name | Type | Nullable | Primary Key | Default |")
        lines.append("|------|------|----------|-------------|---------|")
        for col in table.columns:
            lines.append(
                f"| `{col.name}` | {col.type} | {'Yes' if col.nullable else 'No'} "
                f"| {'Yes' if col.primary_key else 'No'} | {col.default or ''} |"
            )
        lines.append("")

        if table.indexes:
            lines.append("**Indexes:**")
            lines.append("")
            for idx in table.indexes:
                uniq = " (UNIQUE)" if idx.unique else ""
                cols = ", ".join(f"`{c}`" for c in idx.columns)
                lines.append(f"- `{idx.name}`{uniq}: {cols}")
            lines.append("")

        if table.foreign_keys:
            lines.append("**Foreign Keys:**")
            lines.append("")
            for fk in table.foreign_keys:
                lines.append(f"- `{fk.column}` → `{fk.ref_table}`.`{fk.ref_column}`")
            lines.append("")

    return "\n".join(lines)


def export_html(report: SchemaReport) -> str:
    """Render the SchemaReport as a self-contained HTML page with a dark theme."""

    def esc(text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    # Build issues HTML
    issues_html = ""
    if report.issues:
        rows = ""
        for issue in report.issues:
            badge_class = "badge-warn" if issue.severity == "warning" else "badge-info"
            rows += (
                f"<tr><td><span class='badge {badge_class}'>{esc(issue.severity.upper())}</span></td>"
                f"<td><code>{esc(issue.table)}</code></td>"
                f"<td>{esc(issue.message)}</td></tr>\n"
            )
        issues_html = f"""
        <section>
          <h2>Issues <span class="count">{len(report.issues)}</span></h2>
          <table>
            <thead><tr><th>Severity</th><th>Table</th><th>Message</th></tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </section>"""

    # Build tables HTML
    tables_html = ""
    for table in report.tables:
        col_rows = ""
        for col in table.columns:
            pk = "<span class='badge badge-pk'>PK</span>" if col.primary_key else ""
            nullable = "<span class='badge badge-null'>NULL</span>" if col.nullable else ""
            col_rows += (
                f"<tr><td><code>{esc(col.name)}</code></td>"
                f"<td>{esc(col.type)}</td>"
                f"<td>{pk}{nullable}</td>"
                f"<td>{esc(col.default or '')}</td></tr>\n"
            )

        idx_html = ""
        if table.indexes:
            idx_items = ""
            for idx in table.indexes:
                uniq = " <span class='badge badge-uniq'>UNIQUE</span>" if idx.unique else ""
                cols = ", ".join(f"<code>{esc(c)}</code>" for c in idx.columns)
                idx_items += f"<li><code>{esc(idx.name)}</code>{uniq}: {cols}</li>\n"
            idx_html = f"<h4>Indexes</h4><ul>{idx_items}</ul>"

        fk_html = ""
        if table.foreign_keys:
            fk_items = ""
            for fk in table.foreign_keys:
                fk_items += (
                    f"<li><code>{esc(fk.column)}</code> → "
                    f"<code>{esc(fk.ref_table)}.{esc(fk.ref_column)}</code></li>\n"
                )
            fk_html = f"<h4>Foreign Keys</h4><ul>{fk_items}</ul>"

        ai_html = ""
        if table.ai_doc:
            ai_html = f"<p class='ai-doc'>{esc(table.ai_doc)}</p>"

        tables_html += f"""
        <div class='table-card'>
          <div class='table-header'>
            <h3><code>{esc(table.name)}</code></h3>
            <span class='row-count'>{table.row_count} rows</span>
          </div>
          {ai_html}
          <table>
            <thead><tr><th>Column</th><th>Type</th><th>Flags</th><th>Default</th></tr></thead>
            <tbody>{col_rows}</tbody>
          </table>
          {idx_html}{fk_html}
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>schemaspy — {esc(report.db_path)}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{
      margin: 0; padding: 2rem;
      background: #0d1117; color: #c9d1d9;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 15px; line-height: 1.6;
    }}
    h1 {{ color: #58a6ff; font-size: 1.8rem; margin-bottom: 0.25rem; }}
    h2 {{ color: #79c0ff; border-bottom: 1px solid #30363d; padding-bottom: 0.4rem; }}
    h3 {{ color: #e6edf3; margin: 0; }}
    h4 {{ color: #8b949e; margin: 0.8rem 0 0.3rem; }}
    code {{ background: #161b22; border: 1px solid #30363d; border-radius: 4px; padding: 0.1em 0.35em; font-family: "SFMono-Regular", Consolas, monospace; font-size: 0.88em; }}
    table {{ width: 100%; border-collapse: collapse; margin: 0.75rem 0; }}
    th {{ background: #161b22; color: #8b949e; text-align: left; padding: 0.5rem 0.75rem; border: 1px solid #30363d; font-weight: 600; }}
    td {{ padding: 0.45rem 0.75rem; border: 1px solid #21262d; vertical-align: top; }}
    tr:nth-child(even) td {{ background: #0d1117; }}
    tr:nth-child(odd) td {{ background: #161b22; }}
    .meta {{ color: #8b949e; font-size: 0.9rem; margin-bottom: 1.5rem; }}
    .count {{ background: #21262d; border-radius: 12px; padding: 0.1em 0.6em; font-size: 0.82em; color: #8b949e; }}
    .badge {{ display: inline-block; border-radius: 4px; padding: 0.1em 0.45em; font-size: 0.75em; font-weight: 700; margin-right: 2px; }}
    .badge-warn {{ background: #5a3e1b; color: #d29922; }}
    .badge-info {{ background: #1b3a5a; color: #58a6ff; }}
    .badge-pk {{ background: #1b3a5a; color: #58a6ff; }}
    .badge-null {{ background: #2d333b; color: #8b949e; }}
    .badge-uniq {{ background: #1b3a5a; color: #79c0ff; }}
    .table-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 1.25rem; margin-bottom: 1.5rem; }}
    .table-header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem; }}
    .row-count {{ font-size: 0.82rem; color: #8b949e; background: #21262d; border-radius: 12px; padding: 0.1em 0.6em; }}
    .ai-doc {{ background: #0d1117; border-left: 3px solid #58a6ff; padding: 0.6rem 1rem; border-radius: 0 4px 4px 0; color: #8b949e; font-style: italic; margin-bottom: 0.75rem; }}
    section {{ margin-bottom: 2rem; }}
    ul {{ margin: 0.25rem 0 0.5rem 1.25rem; padding: 0; }}
    li {{ margin-bottom: 0.2rem; }}
    footer {{ margin-top: 3rem; color: #484f58; font-size: 0.8rem; border-top: 1px solid #21262d; padding-top: 1rem; }}
  </style>
</head>
<body>
  <h1>schemaspy</h1>
  <p class="meta">
    <strong>Database:</strong> <code>{esc(report.db_path)}</code> &nbsp;|&nbsp;
    <strong>Tables:</strong> {len(report.tables)} &nbsp;|&nbsp;
    <strong>Generated:</strong> {esc(report.generated_at)}
  </p>
  {issues_html}
  <section>
    <h2>Tables <span class="count">{len(report.tables)}</span></h2>
    {tables_html}
  </section>
  <footer>Generated by <strong>schemaspy v1.0.0</strong></footer>
</body>
</html>"""
