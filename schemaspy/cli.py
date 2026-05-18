"""CLI entry point for schemaspy."""

from __future__ import annotations

import argparse
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
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="schemaspy",
        description="SQLite schema explorer with AI documentation and semantic search",
    )
    parser.add_argument("--version", action="version", version="schemaspy 1.0.0")

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

    args = parser.parse_args()

    dispatch = {
        "inspect": cmd_inspect,
        "similar": cmd_similar,
        "issues": cmd_issues,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
