"""Tests for schemaspy.analyzer using in-memory/temp SQLite databases."""

import os
import sqlite3
import tempfile

from schemaspy.analyzer import analyze_schema


def _make_db() -> str:
    """Create a temp SQLite DB with users + posts tables."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE
        );
        CREATE TABLE posts (
            id INTEGER PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            title TEXT,
            body TEXT
        );
        INSERT INTO users VALUES (1, 'Alice', 'alice@example.com');
        INSERT INTO posts VALUES (1, 1, 'Hello', 'World');
    """)
    con.close()
    return path


def test_analyze_tables() -> None:
    path = _make_db()
    try:
        report = analyze_schema(path)
        assert len(report.tables) == 2
        names = {t.name for t in report.tables}
        assert "users" in names and "posts" in names
    finally:
        os.unlink(path)


def test_row_counts() -> None:
    path = _make_db()
    try:
        report = analyze_schema(path)
        users = next(t for t in report.tables if t.name == "users")
        assert users.row_count == 1
    finally:
        os.unlink(path)


def test_detect_fk_issue() -> None:
    path = _make_db()
    try:
        report = analyze_schema(path)
        # posts.user_id references users.id but has no explicit index → should flag
        issue_tables = {i.table for i in report.issues}
        assert "posts" in issue_tables
    finally:
        os.unlink(path)


def test_columns_populated() -> None:
    path = _make_db()
    try:
        report = analyze_schema(path)
        users = next(t for t in report.tables if t.name == "users")
        col_names = {c.name for c in users.columns}
        assert "id" in col_names
        assert "email" in col_names
    finally:
        os.unlink(path)


def test_primary_key_detected() -> None:
    path = _make_db()
    try:
        report = analyze_schema(path)
        users = next(t for t in report.tables if t.name == "users")
        pk_cols = [c for c in users.columns if c.primary_key]
        assert len(pk_cols) == 1
        assert pk_cols[0].name == "id"
    finally:
        os.unlink(path)


def test_foreign_keys_detected() -> None:
    path = _make_db()
    try:
        report = analyze_schema(path)
        posts = next(t for t in report.tables if t.name == "posts")
        assert len(posts.foreign_keys) == 1
        fk = posts.foreign_keys[0]
        assert fk.column == "user_id"
        assert fk.ref_table == "users"
    finally:
        os.unlink(path)


def test_empty_database() -> None:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        report = analyze_schema(path)
        assert report.tables == []
        assert report.issues == []
    finally:
        os.unlink(path)


def test_generated_at_set() -> None:
    path = _make_db()
    try:
        report = analyze_schema(path)
        assert report.generated_at != ""
    finally:
        os.unlink(path)
