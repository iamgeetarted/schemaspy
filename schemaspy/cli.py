"""CLI entry point for schemaspy."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def _require_db(path: str) -> None:
    if not os.path.isfile(path):
        console.print(f"[red]Error:[/red] File not found: {path}")
        sys.exit(1)


def _get_ai_client() -> object:
    """Return an Anthropic client, exiting if API key is missing."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        console.print(
            "[red]Error:[/red] ANTHROPIC_API_KEY environment variable is not set.\n"
            "Set it to use AI documentation features."
        )
        sys.exit(1)
    try:
        import anthropic  # type: ignore[import]
        return anthropic.Anthropic(api_key=api_key)
    except ImportError:
        console.print("[red]Error:[/red] The 'anthropic' package is required for AI features.")
        sys.exit(1)


def _issues_panel(issues: list) -> Panel:
    """Build a Rich panel summarising schema issues."""
    from rich.table import Table as RTable

    tbl = RTable(show_header=True, header_style="bold", box=None, padding=(0, 1))
    tbl.add_column("Severity", style="bold")
    tbl.add_column("Table", style="cyan")
    tbl.add_column("Message")
    for issue in issues:
        sev_style = "yellow" if issue.severity == "warning" else "blue"
        tbl.add_row(
            Text(issue.severity.upper(), style=sev_style),
            issue.table,
            issue.message,
        )
    return Panel(tbl, title="[bold red]Schema Issues[/bold red]", border_style="red")


# ---------------------------------------------------------------------------
# Sub-command: inspect
# ---------------------------------------------------------------------------

def cmd_inspect(args: argparse.Namespace) -> None:
    from schemaspy.analyzer import analyze_schema

    _require_db(args.db)
    with console.status("[cyan]Analyzing schema…[/cyan]"):
        report = analyze_schema(args.db)

    # ── AI documentation ────────────────────────────────────────────────────
    if args.ai:
        from schemaspy.ai_doc import stream_issues_doc, stream_table_doc

        client = _get_ai_client()
        with Live(console=console, refresh_per_second=4) as live:
            for table in report.tables:
                live.update(
                    Panel(
                        f"[cyan]Documenting table:[/cyan] [bold]{table.name}[/bold]",
                        border_style="cyan",
                    )
                )
                table.ai_doc = stream_table_doc(table, client)

            if report.issues:
                live.update(
                    Panel("[cyan]Generating issues summary…[/cyan]", border_style="cyan")
                )
                issues_ai = stream_issues_doc(report.issues, client)
            else:
                issues_ai = ""

            live.update(Panel("[green]✓ Documentation complete[/green]", border_style="green"))

        if issues_ai:
            console.print(
                Panel(issues_ai, title="[bold yellow]AI Issues Summary[/bold yellow]", border_style="yellow")
            )

    # ── Export ───────────────────────────────────────────────────────────────
    if args.format:
        from schemaspy.exporter import export_html, export_json, export_markdown

        fmt = args.format.lower()
        if fmt == "json":
            output = export_json(report)
        elif fmt == "markdown":
            output = export_markdown(report)
        elif fmt == "html":
            output = export_html(report)
        else:
            console.print(f"[red]Unknown format:[/red] {fmt}")
            sys.exit(1)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(output)
            console.print(f"[green]✓[/green] Exported to [cyan]{args.output}[/cyan]")
        else:
            console.print(output)
        return

    # ── Rich summary table ───────────────────────────────────────────────────
    issue_tables = {i.table for i in report.issues}

    summary = Table(
        title=f"[bold]Schema: {report.db_path}[/bold]",
        show_header=True,
        header_style="bold magenta",
    )
    summary.add_column("Table", style="cyan", no_wrap=True)
    summary.add_column("Rows", justify="right")
    summary.add_column("Columns", justify="right")
    summary.add_column("Indexes", justify="right")
    summary.add_column("FKs", justify="right")
    summary.add_column("Issues", justify="center")

    for table in report.tables:
        has_issue = table.name in issue_tables
        row_style = "" if not has_issue else "yellow"
        summary.add_row(
            table.name,
            str(table.row_count),
            str(len(table.columns)),
            str(len(table.indexes)),
            str(len(table.foreign_keys)),
            "[yellow]⚠[/yellow]" if has_issue else "[green]✓[/green]",
            style=row_style,
        )

    console.print(summary)

    if args.ai:
        console.print()
        for table in report.tables:
            if table.ai_doc:
                console.print(
                    Panel(
                        table.ai_doc,
                        title=f"[bold cyan]{table.name}[/bold cyan]",
                        border_style="cyan",
                    )
                )

    if report.issues:
        console.print()
        console.print(_issues_panel(report.issues))


# ---------------------------------------------------------------------------
# Sub-command: similar
# ---------------------------------------------------------------------------

def cmd_similar(args: argparse.Namespace) -> None:
    from schemaspy.analyzer import analyze_schema
    from schemaspy.semantic import find_similar_tables

    _require_db(args.db)
    with console.status("[cyan]Analyzing schema…[/cyan]"):
        report = analyze_schema(args.db)

    results = find_similar_tables(args.query, report.tables, top_k=args.top_k)

    tbl = Table(
        title=f'[bold]Similar tables for:[/bold] "{args.query}"',
        show_header=True,
        header_style="bold magenta",
    )
    tbl.add_column("Rank", justify="right", style="dim")
    tbl.add_column("Table", style="cyan")
    tbl.add_column("Score", justify="right")
    tbl.add_column("Columns")

    for rank, (table, score) in enumerate(results, 1):
        col_names = ", ".join(c.name for c in table.columns[:6])
        if len(table.columns) > 6:
            col_names += f" (+{len(table.columns) - 6} more)"
        tbl.add_row(str(rank), table.name, f"{score:.4f}", col_names)

    console.print(tbl)


# ---------------------------------------------------------------------------
# Sub-command: issues
# ---------------------------------------------------------------------------

def cmd_issues(args: argparse.Namespace) -> None:
    from schemaspy.analyzer import analyze_schema

    _require_db(args.db)
    with console.status("[cyan]Analyzing schema…[/cyan]"):
        report = analyze_schema(args.db)

    if not report.issues:
        console.print("[green]✓ No issues detected.[/green]")
        return

    console.print(_issues_panel(report.issues))

    if args.ai:
        from schemaspy.ai_doc import stream_issues_doc

        client = _get_ai_client()
        full_text = ""
        with Live(console=console, refresh_per_second=4) as live:
            live.update(Panel("[cyan]Generating AI explanation…[/cyan]", border_style="cyan"))
            full_text = stream_issues_doc(report.issues, client)
            live.update(Panel("[green]✓ Done[/green]", border_style="green"))

        console.print(
            Panel(
                full_text,
                title="[bold yellow]AI Issue Explanation[/bold yellow]",
                border_style="yellow",
            )
        )


# ---------------------------------------------------------------------------
# Sub-command: profile
# ---------------------------------------------------------------------------

def cmd_profile(args: argparse.Namespace) -> None:
    """Profile column statistics for one or all tables in a SQLite database."""
    from schemaspy.analyzer import analyze_schema
    from schemaspy.profiler import ColumnProfile, profile_database, profile_table

    _require_db(args.db)

    with console.status("[cyan]Analyzing schema…[/cyan]"):
        report = analyze_schema(args.db)

    # Filter to requested table if --table given
    tables = report.tables
    if args.table:
        tables = [t for t in tables if t.name == args.table]
        if not tables:
            console.print(f"[red]Error:[/red] Table '{args.table}' not found in database.")
            sys.exit(1)

    async def _collect() -> dict[str, list[ColumnProfile]]:
        tasks = [
            asyncio.to_thread(profile_table, args.db, t) for t in tables
        ]
        results = await asyncio.gather(*tasks)
        return {t.name: profiles for t, profiles in zip(tables, results)}

    with console.status("[cyan]Profiling columns…[/cyan]"):
        all_profiles = asyncio.run(_collect())

    # Flatten for output
    flat: list[ColumnProfile] = []
    for t in tables:
        flat.extend(all_profiles.get(t.name, []))

    fmt = (args.format or "table").lower()

    # ── JSON ─────────────────────────────────────────────────────────────────
    if fmt == "json":
        import dataclasses
        console.print(json.dumps([dataclasses.asdict(p) for p in flat], indent=2))
        return

    # ── Markdown ─────────────────────────────────────────────────────────────
    if fmt == "markdown":
        header = "| Table | Column | Type | Rows | Null% | Distinct | Min | Max | Sample |"
        sep    = "|-------|--------|------|------|-------|----------|-----|-----|--------|"
        lines = [header, sep]
        for p in flat:
            sample = ", ".join(p.sample_vals[:3])
            lines.append(
                f"| {p.table_name} | {p.col_name} | {p.col_type} "
                f"| {p.row_count} | {p.null_pct:.1f}% | {p.distinct_count} "
                f"| {p.min_val or ''} | {p.max_val or ''} | {sample} |"
            )
        console.print("\n".join(lines))
        return

    # ── Rich table (default) ─────────────────────────────────────────────────
    tbl = Table(
        title=f"[bold]Column Profiles: {args.db}[/bold]",
        show_header=True,
        header_style="bold magenta",
    )
    tbl.add_column("Table", style="cyan", no_wrap=True)
    tbl.add_column("Column", style="bold")
    tbl.add_column("Type", style="dim")
    tbl.add_column("Rows", justify="right")
    tbl.add_column("Null%", justify="right")
    tbl.add_column("Distinct", justify="right")
    tbl.add_column("Min")
    tbl.add_column("Max")
    tbl.add_column("Sample")

    for p in flat:
        null_style = "red" if p.null_pct > 50 else ("yellow" if p.null_pct > 0 else "green")
        tbl.add_row(
            p.table_name,
            p.col_name,
            p.col_type,
            str(p.row_count),
            Text(f"{p.null_pct:.1f}%", style=null_style),
            str(p.distinct_count),
            p.min_val or "[dim]—[/dim]",
            p.max_val or "[dim]—[/dim]",
            ", ".join(p.sample_vals[:3]) or "[dim]—[/dim]",
        )

    console.print(tbl)


# ---------------------------------------------------------------------------
# Sub-command: diff
# ---------------------------------------------------------------------------

def cmd_diff(args: argparse.Namespace) -> None:
    """Show structural differences between two SQLite database schemas."""
    from schemaspy.analyzer import analyze_schema
    from schemaspy.differ import diff_schemas

    _require_db(args.old_db)
    _require_db(args.new_db)

    with console.status("[cyan]Analyzing schemas…[/cyan]"):
        old_report = analyze_schema(args.old_db)
        new_report = analyze_schema(args.new_db)

    diff = diff_schemas(old_report, new_report)

    if not diff.has_changes:
        console.print("[green]✓ Schemas are identical — no differences found.[/green]")
        sys.exit(0)

    # ── Added tables ─────────────────────────────────────────────────────────
    if diff.added_tables:
        console.print()
        console.print("[bold green]Added tables:[/bold green]")
        for name in diff.added_tables:
            console.print(f"  [green]+ {name}[/green]")

    # ── Removed tables ────────────────────────────────────────────────────────
    if diff.removed_tables:
        console.print()
        console.print("[bold red]Removed tables:[/bold red]")
        for name in diff.removed_tables:
            console.print(f"  [red]- {name}[/red]")

    # ── Changed tables ────────────────────────────────────────────────────────
    if diff.changed_tables:
        console.print()
        console.print("[bold yellow]Changed tables:[/bold yellow]")
        for table_name, changes in diff.changed_tables.items():
            console.print(f"\n  [cyan]{table_name}[/cyan]")
            for col in changes.added_columns:
                console.print(f"    [green]+ column: {col}[/green]")
            for col in changes.removed_columns:
                console.print(f"    [red]- column: {col}[/red]")
            for col, (old_type, new_type) in changes.type_changes.items():
                console.print(
                    f"    [yellow]~ column: {col}  "
                    f"[dim]{old_type}[/dim] → [bold]{new_type}[/bold][/yellow]"
                )

    console.print()
    # Exit 1 so CI pipelines can detect schema drift
    sys.exit(1)


# ---------------------------------------------------------------------------
# Sub-command: query (natural language → SQL via Claude)
# ---------------------------------------------------------------------------

def cmd_query(args: argparse.Namespace) -> None:
    """Generate SQL from a natural-language question using Claude, optionally execute it."""
    from schemaspy.analyzer import analyze_schema

    _require_db(args.db)

    with console.status("[cyan]Analyzing schema…[/cyan]"):
        report = analyze_schema(args.db)

    # Build a schema context string for the prompt
    schema_lines: list[str] = []
    for table in report.tables:
        col_defs = ", ".join(
            f"{c.name} {c.type}" for c in table.columns
        )
        schema_lines.append(f"  {table.name}({col_defs})")
        for fk in table.foreign_keys:
            schema_lines.append(
                f"    -- FK: {table.name}.{fk.column} → {fk.ref_table}.{fk.ref_column}"
            )

    schema_context = "\n".join(schema_lines)

    prompt = (
        "You are a SQLite expert. Given the schema below, write a single valid SQLite SQL "
        "query that answers the question. Output ONLY the raw SQL with no markdown fences, "
        "no explanation, and no trailing semicolon unless required by syntax.\n\n"
        f"Schema:\n{schema_context}\n\n"
        f"Question: {args.question}"
    )

    client = _get_ai_client()

    # Lazy import anthropic inside function
    import anthropic  # type: ignore[import]

    sql_text = ""

    with Live(console=console, refresh_per_second=8) as live:
        live.update(Panel("[cyan]Generating SQL…[/cyan]", border_style="cyan"))
        with client.messages.stream(  # type: ignore[attr-defined]
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for chunk in stream.text_stream:
                sql_text += chunk
                live.update(
                    Panel(
                        sql_text,
                        title="[bold cyan]Generated SQL[/bold cyan]",
                        border_style="cyan",
                    )
                )
        live.update(
            Panel(
                sql_text,
                title="[bold green]Generated SQL[/bold green]",
                border_style="green",
            )
        )

    console.print()

    # ── Execute ──────────────────────────────────────────────────────────────
    if args.execute:
        import sqlite3

        sql_to_run = sql_text.strip()
        # Append LIMIT if not already present and user specified one
        if args.limit and "limit" not in sql_to_run.lower():
            sql_to_run = f"{sql_to_run} LIMIT {args.limit}"

        try:
            con = sqlite3.connect(args.db)
            try:
                cur = con.execute(sql_to_run)
                rows = cur.fetchall()
                col_names = [desc[0] for desc in cur.description] if cur.description else []
            finally:
                con.close()
        except sqlite3.Error as exc:
            console.print(f"[red]SQL Error:[/red] {exc}")
            sys.exit(1)

        result_tbl = Table(
            title=f"[bold]Query Results[/bold] ({len(rows)} row{'s' if len(rows) != 1 else ''})",
            show_header=True,
            header_style="bold magenta",
        )
        for col_name in col_names:
            result_tbl.add_column(col_name)

        for row in rows:
            result_tbl.add_row(*[str(v) if v is not None else "[dim]NULL[/dim]" for v in row])

        console.print(result_tbl)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="schemaspy",
        description="SQLite schema explorer with AI documentation and semantic search",
    )
    parser.add_argument("--version", action="version", version="schemaspy 1.3.0")

    sub = parser.add_subparsers(dest="command", required=True)

    # inspect
    p_inspect = sub.add_parser("inspect", help="Analyze and display a database schema")
    p_inspect.add_argument("db", metavar="DB", help="Path to SQLite database file")
    p_inspect.add_argument("--ai", action="store_true", help="Generate AI documentation")
    p_inspect.add_argument(
        "--format", choices=["json", "markdown", "html"], help="Export format"
    )
    p_inspect.add_argument("--output", "-o", metavar="FILE", help="Output file path")

    # similar
    p_similar = sub.add_parser("similar", help="Find semantically similar tables")
    p_similar.add_argument("db", metavar="DB", help="Path to SQLite database file")
    p_similar.add_argument("query", metavar="QUERY", help="Search query")
    p_similar.add_argument("--top-k", type=int, default=5, help="Number of results (default: 5)")

    # issues
    p_issues = sub.add_parser("issues", help="Show schema issues")
    p_issues.add_argument("db", metavar="DB", help="Path to SQLite database file")
    p_issues.add_argument("--ai", action="store_true", help="Generate AI explanation of issues")

    # profile
    p_profile = sub.add_parser("profile", help="Profile column statistics for a database")
    p_profile.add_argument("db", metavar="DB", help="Path to SQLite database file")
    p_profile.add_argument("--table", metavar="TABLE", help="Limit profiling to a single table")
    p_profile.add_argument(
        "--format",
        choices=["json", "markdown", "table"],
        default="table",
        help="Output format (default: table)",
    )

    # diff
    p_diff = sub.add_parser("diff", help="Show structural differences between two schemas")
    p_diff.add_argument("old_db", metavar="OLD_DB", help="Path to the old SQLite database file")
    p_diff.add_argument("new_db", metavar="NEW_DB", help="Path to the new SQLite database file")

    # query
    p_query = sub.add_parser("query", help="Generate SQL from a natural-language question")
    p_query.add_argument("db", metavar="DB", help="Path to SQLite database file")
    p_query.add_argument("question", metavar="QUESTION", help="Natural-language question")
    p_query.add_argument(
        "--execute", action="store_true", help="Execute the generated SQL and display results"
    )
    p_query.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Append LIMIT N to the generated query before executing",
    )

    args = parser.parse_args()

    dispatch = {
        "inspect": cmd_inspect,
        "similar": cmd_similar,
        "issues": cmd_issues,
        "profile": cmd_profile,
        "diff": cmd_diff,
        "query": cmd_query,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
