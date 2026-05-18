# schemaspy

**SQLite schema explorer with AI documentation generation, semantic table search, and async Rich dashboard.**

Understand any SQLite database in seconds: inspect tables, detect schema issues, generate AI-powered documentation with streaming Claude, and find semantically related tables using pure-Python TF-IDF cosine similarity — all from a beautiful terminal UI.

---

## Breakthrough Techniques

| Technique | Description |
|---|---|
| **LLM Integration** | Streaming Claude Haiku (`claude-haiku-4-5-20251001`) generates concise table documentation and schema-issue explanations in real time. Tokens stream directly into a Rich Live panel. |
| **Semantic Vector Search** | Pure Python TF-IDF cosine similarity finds tables and columns semantically similar to a natural-language query — zero dependencies beyond the stdlib. No numpy required. |
| **Full Async Architecture** | `asyncio.TaskGroup` (Python 3.11+) analyzes all tables concurrently via `asyncio.to_thread`, parallelizing I/O-bound SQLite PRAGMA calls across the full schema. |
| **Live Rich UI** | `rich.live.Live` context drives a real-time dashboard: spinners update as each table is documented and the progress panel refreshes at 4 fps with zero flicker. |

---

## Installation

```bash
# From source
git clone https://github.com/iamgeetarted/schemaspy.git
cd schemaspy
pip install -e .

# Or directly
pip install git+https://github.com/iamgeetarted/schemaspy.git
```

**Requirements:** Python 3.11+, `rich`, `anthropic` (only needed for `--ai` flag).

---

## Quick Start

```bash
# Inspect a database schema
schemaspy inspect myapp.db

# Generate AI documentation for every table (requires ANTHROPIC_API_KEY)
export ANTHROPIC_API_KEY=sk-ant-...
schemaspy inspect myapp.db --ai

# Find tables related to a concept
schemaspy similar myapp.db "user authentication and sessions"

# Show only schema issues, with AI explanation
schemaspy issues myapp.db --ai

# Export to HTML report
schemaspy inspect myapp.db --format html --output report.html
```

---

## Command Reference

### `schemaspy inspect <db>`

Analyze and display a complete schema summary.

| Flag | Description |
|---|---|
| `--ai` | Stream AI documentation for every table using Claude Haiku |
| `--format json\|markdown\|html` | Export the report in the specified format |
| `--output FILE` / `-o FILE` | Write export output to a file instead of stdout |

**Example — plain inspect:**

```
$ schemaspy inspect blog.db

                  Schema: blog.db
┏━━━━━━━━━━┳━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━┳━━━━━━━━┓
┃ Table    ┃ Rows ┃ Columns ┃ Indexes ┃ FKs ┃ Issues ┃
┡━━━━━━━━━━╇━━━━━━╇━━━━━━━━━╇━━━━━━━━━╇━━━━━╇━━━━━━━━┩
│ comments │    8 │       5 │       1 │   2 │   ⚠    │
│ posts    │   24 │       7 │       2 │   1 │   ✓    │
│ tags     │   12 │       3 │       1 │   0 │   ✓    │
│ users    │    6 │       6 │       2 │   0 │   ✓    │
└──────────┴──────┴─────────┴─────────┴─────┴────────┘

╭─────────────── Schema Issues ────────────────╮
│ WARNING  comments  FK 'post_id' has no index │
╰──────────────────────────────────────────────╯
```

**Example — AI documentation (`--ai`):**

```
$ schemaspy inspect blog.db --ai

╭─ Documenting table: users ──────────────────╮
│ ...streaming...                              │
╰──────────────────────────────────────────────╯

╭─ users ─────────────────────────────────────╮
│ The users table stores registered accounts, │
│ holding authentication credentials and      │
│ profile metadata. It acts as the root       │
│ entity referenced by posts and comments.    │
╰──────────────────────────────────────────────╯
```

---

### `schemaspy similar <db> "<query>"`

Find the tables most semantically similar to a natural-language query using TF-IDF cosine similarity.

| Flag | Default | Description |
|---|---|---|
| `--top-k N` | 5 | Number of results to return |

**Example:**

```
$ schemaspy similar ecommerce.db "payment billing invoice" --top-k 4

     Similar tables for: "payment billing invoice"
┏━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Rank ┃ Table           ┃  Score ┃ Columns                      ┃
┡━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│    1 │ invoices        │ 0.8312 │ id, order_id, amount, paid_at │
│    2 │ payments        │ 0.7109 │ id, invoice_id, method, total │
│    3 │ orders          │ 0.2841 │ id, user_id, status, total    │
│    4 │ products        │ 0.0412 │ id, name, price, sku          │
└──────┴─────────────────┴────────┴──────────────────────────────┘
```

---

### `schemaspy issues <db>`

Show schema quality issues detected in the database.

| Flag | Description |
|---|---|
| `--ai` | Stream an AI explanation prioritizing which issues to fix first |

**Detected issue types:**

| Issue | Severity | Description |
|---|---|---|
| FK column missing index | warning | Foreign key column has no index — leads to full table scans on joins |
| No primary key | warning | Table has no PK column — makes row identification ambiguous |
| Empty table | info | Table exists but contains no rows |

**Example:**

```
$ schemaspy issues legacy.db --ai

╭──────────────────── Schema Issues ─────────────────────╮
│ WARNING  orders    FK 'customer_id' has no index        │
│ WARNING  shipments  Table has no primary key column     │
│ INFO     audit_log  Table has no rows                   │
╰─────────────────────────────────────────────────────────╯

╭────────────── AI Issue Explanation ────────────────────╮
│ The most critical issue is the missing index on         │
│ orders.customer_id — every join to the customers table  │
│ will trigger a full scan of orders, which degrades      │
│ linearly with row count. Fix that first by running:     │
│ CREATE INDEX idx_orders_customer_id ON orders(...)      │
╰─────────────────────────────────────────────────────────╯
```

---

## Export Formats

```bash
# JSON — machine-readable full report
schemaspy inspect myapp.db --format json --output schema.json

# Markdown — docs-friendly report
schemaspy inspect myapp.db --format markdown --output SCHEMA.md

# HTML — self-contained dark-theme report, no external dependencies
schemaspy inspect myapp.db --format html --output schema.html
```

---

## What's New in v1.0.0

- **Initial release** of schemaspy
- Full SQLite schema introspection via PRAGMA commands (table_info, index_list, foreign_key_list)
- Async schema analysis with `asyncio.TaskGroup` for concurrent table analysis (Python 3.11+)
- Pure Python TF-IDF semantic similarity search — no numpy, no external ML libraries
- Streaming Claude Haiku integration for per-table documentation and issue explanations
- Real-time Rich Live UI with spinner panels that update as documentation streams
- Three export formats: JSON, Markdown, self-contained dark-theme HTML
- Three CLI commands: `inspect`, `similar`, `issues`
- Comprehensive test suite (analyzer, semantic, exporter)

---

## Architecture

```
schemaspy/
├── models.py      — Dataclasses: TableInfo, ColumnInfo, SchemaReport, SchemaIssue
├── analyzer.py    — SQLite introspection via stdlib sqlite3 + async TaskGroup
├── semantic.py    — TF-IDF cosine similarity (pure Python, stdlib only)
├── ai_doc.py      — Streaming Claude Haiku documentation generator
├── exporter.py    — Markdown / JSON / HTML rendering
└── cli.py         — Argparse CLI with Rich Live output
```

---

## License

MIT — see [LICENSE](LICENSE) for details.
