## What's New in v1.4

### Feature 1 — Schema Health Score (`schemaspy health`)

Get an instant 0–100 health score for your database schema with a letter grade (A–F) and a per-category breakdown table. Six weighted dimensions are evaluated: primary keys, FK index coverage, naming conventions, empty tables, column type declarations, and index coverage on large tables.

```bash
schemaspy health myapp.db
```

Output shows a progress-bar-style score for each category, the contributing weight, and specific details about what passed or needs attention. The overall score and grade are printed in a colour-coded summary panel.

---

### Feature 2 — Query Plan Analyzer (`schemaspy analyze-query`)

Pass any SQL statement and get a formatted EXPLAIN QUERY PLAN table showing each plan step, whether an index was used, and which index — plus actionable `CREATE INDEX` suggestions for any full-table scans detected.

```bash
schemaspy analyze-query myapp.db "SELECT * FROM orders WHERE customer_id = 42"
```

Full table scans are highlighted in red, indexed scans in green. Each suggestion includes the exact `CREATE INDEX` DDL you can run to fix the issue.

---

### Feature 3 — Dedicated Schema Export (`schemaspy export`)

A first-class `export` command that supports five formats including the new **SQL DDL** format, which emits `DROP TABLE IF EXISTS` + `CREATE TABLE` + `CREATE INDEX` statements — a runnable script to recreate the schema from scratch.

```bash
# Recreatable SQL DDL (new!)
schemaspy export myapp.db --format sql --output schema.sql

# Mermaid ER diagram
schemaspy export myapp.db --format mermaid --output schema.mmd

# JSON, Markdown, or self-contained HTML
schemaspy export myapp.db --format json --output schema.json
schemaspy export myapp.db --format markdown --output SCHEMA.md
schemaspy export myapp.db --format html --output report.html
```

---

## What's New in v1.3

### Feature 1 — Data Profiling (`schemaspy profile`)

Profile every column in a database: null counts, distinct counts, min/max values, and sample data — all computed with pure SQL, no extra dependencies.

```bash
# Profile all tables (Rich table output)
schemaspy profile myapp.db

# Profile a single table
schemaspy profile myapp.db --table users

# Export as JSON or Markdown
schemaspy profile myapp.db --format json
schemaspy profile myapp.db --format markdown
```

Output columns: **Table · Column · Type · Rows · Null% · Distinct · Min · Max · Sample**

---

### Feature 2 — Schema Diff (`schemaspy diff`)

Compare two SQLite databases and surface every structural change: added/removed tables, added/removed columns, and column type changes. Exits with code 1 when differences are found, making it CI-friendly.

```bash
schemaspy diff old.db new.db
```

Added tables print in green, removed tables in red, and column changes show `old_type → new_type` in yellow.

---

### Feature 3 — Natural Language to SQL (`schemaspy query`)

Ask a question in plain English and get valid SQLite SQL back, streamed live from Claude Haiku. Optionally execute the query immediately and display results in a Rich table.

```bash
# Generate SQL only (requires ANTHROPIC_API_KEY)
export ANTHROPIC_API_KEY=sk-ant-...
schemaspy query myapp.db "How many orders were placed per user last month?"

# Generate AND execute, capping results at 20 rows
schemaspy query myapp.db "Top 5 products by revenue" --execute --limit 20
```

---

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

### `schemaspy health <db>`

Score the schema health across six weighted quality dimensions and display a breakdown with an overall letter grade (A–F).

**Scored dimensions:**

| Category | Weight | What is checked |
|---|---|---|
| Primary Keys | 25 | Every table has a PK column |
| FK Indexes | 20 | Every FK column is indexed |
| Naming Conventions | 15 | All identifiers use snake_case |
| Column Types | 15 | All columns have explicit type declarations |
| Index Coverage | 15 | Large tables (≥100 rows) have at least one explicit index |
| Non-empty Tables | 10 | No vestigial empty tables |

**Example:**

```
$ schemaspy health legacy.db

                 Schema Health: legacy.db
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Category             ┃         Score ┃ Weight ┃ Details                   ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Primary Keys         │ ██████████ 100 │     25 │ All tables have a PK      │
│ FK Indexes           │ ███░░░░░░░  33 │     20 │ Unindexed: orders.user_id │
│ Naming Conventions   │ ██████████ 100 │     15 │ All identifiers snake_case │
│ Column Types         │ ██████████ 100 │     15 │ All columns typed         │
│ Index Coverage       │ █████░░░░░  50 │     15 │ Under-indexed: orders     │
│ Non-empty Tables     │ ██████████ 100 │     10 │ All tables contain data   │
└──────────────────────┴───────────────┴────────┴───────────────────────────┘

╭─── Overall Health Score ────╮
│  78/100  Grade: C           │
╰─────────────────────────────╯
```

---

### `schemaspy analyze-query <db> "<sql>"`

Run `EXPLAIN QUERY PLAN` on any SQL statement and get a formatted table of plan steps (with index-use highlighted), a summary of full scans vs indexed scans, and specific `CREATE INDEX` DDL suggestions.

**Example:**

```
$ schemaspy analyze-query shop.db "SELECT * FROM orders WHERE customer_id = 1"

            EXPLAIN QUERY PLAN
┏━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ ID ┃ Parent ┃ Detail                        ┃ Index Used ┃ Type      ┃
┡━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━┩
│  2 │      0 │ SCAN orders                   │ —          │ FULL SCAN │
└────┴────────┴───────────────────────────────┴────────────┴───────────┘

Steps: 1  Indexed scans: 0  Full scans: 1

╭─── Suggestions ────────────────────────────────────────────────────────────╮
│ 1. Full table scan on 'orders'. Consider:                                  │
│    CREATE INDEX idx_orders_customer_id ON orders(customer_id);             │
╰────────────────────────────────────────────────────────────────────────────╯
```

---

### `schemaspy export <db> --format <fmt>`

Dedicated export command supporting five output formats, including **SQL DDL** which generates a runnable `CREATE TABLE` + `CREATE INDEX` script to recreate the schema from scratch.

| Format | Description |
|---|---|
| `sql` | SQL DDL — DROP/CREATE TABLE + CREATE INDEX statements |
| `mermaid` | Mermaid ER diagram (paste into any Mermaid-compatible renderer) |
| `json` | Machine-readable full schema report |
| `markdown` | Documentation-friendly Markdown |
| `html` | Self-contained dark-theme HTML report |

**Example:**

```bash
# Recreatable SQL DDL
schemaspy export myapp.db --format sql --output schema.sql

# ER diagram for documentation
schemaspy export myapp.db --format mermaid --output schema.mmd

# Print to stdout (omit --output)
schemaspy export myapp.db --format json
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
├── models.py         — Dataclasses: TableInfo, ColumnInfo, SchemaReport, SchemaIssue
├── analyzer.py       — SQLite introspection via stdlib sqlite3 + async TaskGroup
├── semantic.py       — TF-IDF cosine similarity (pure Python, stdlib only)
├── ai_doc.py         — Streaming Claude Haiku documentation generator
├── exporter.py       — Markdown / JSON / HTML / Mermaid / SQL DDL rendering
├── health.py         — Schema health scoring (0-100, A-F grade, 6 weighted categories)
├── query_analyzer.py — EXPLAIN QUERY PLAN runner with index suggestion engine
├── profiler.py       — Column-level data profiling (null %, distinct, min/max, samples)
├── differ.py         — Schema diff: added/removed tables, column changes, type changes
└── cli.py            — Argparse CLI with Rich Live output
```

---

## License

MIT — see [LICENSE](LICENSE) for details.
