"""Tests for schemaspy.semantic TF-IDF similarity search."""

from schemaspy.models import ColumnInfo, TableInfo
from schemaspy.semantic import find_similar_tables, _tokenize, _idf, _cosine


def _make_tables() -> list[TableInfo]:
    return [
        TableInfo(
            name="users",
            columns=[
                ColumnInfo("id", "INTEGER", False, True),
                ColumnInfo("email", "TEXT", True, False),
            ],
        ),
        TableInfo(
            name="products",
            columns=[
                ColumnInfo("id", "INTEGER", False, True),
                ColumnInfo("price", "REAL", True, False),
            ],
        ),
        TableInfo(
            name="auth_tokens",
            columns=[
                ColumnInfo("id", "INTEGER", False, True),
                ColumnInfo("user_id", "INTEGER", False, False),
                ColumnInfo("token", "TEXT", False, False),
            ],
        ),
    ]


def test_find_similar_basic() -> None:
    tables = _make_tables()
    results = find_similar_tables("user authentication login", tables, top_k=3)
    assert len(results) > 0
    names = [t.name for t, _ in results]
    # users or auth_tokens should rank higher than products
    assert "products" not in names[:1]


def test_find_similar_scores() -> None:
    tables = _make_tables()
    results = find_similar_tables("price cost amount", tables, top_k=3)
    assert all(0.0 <= score <= 1.0 for _, score in results)


def test_find_similar_empty() -> None:
    assert find_similar_tables("test", [], top_k=5) == []


def test_find_similar_top_k_respected() -> None:
    tables = _make_tables()
    results = find_similar_tables("data", tables, top_k=2)
    assert len(results) <= 2


def test_find_similar_scores_sorted() -> None:
    tables = _make_tables()
    results = find_similar_tables("user email", tables, top_k=3)
    scores = [s for _, s in results]
    assert scores == sorted(scores, reverse=True)


def test_tokenize() -> None:
    assert _tokenize("user_id") == ["user", "id"]
    assert _tokenize("CamelCase") == ["camelcase"]
    assert _tokenize("foo123bar") == ["foo", "bar"]
    assert _tokenize("") == []


def test_idf_single_doc() -> None:
    idf = _idf([["hello", "world"]])
    assert "hello" in idf
    assert "world" in idf
    assert all(v > 0 for v in idf.values())


def test_cosine_identical() -> None:
    a = [1.0, 2.0, 3.0]
    assert abs(_cosine(a, a) - 1.0) < 1e-9


def test_cosine_zero_vector() -> None:
    assert _cosine([0.0, 0.0], [1.0, 2.0]) == 0.0


def test_find_similar_products_for_price() -> None:
    tables = _make_tables()
    results = find_similar_tables("price cost", tables, top_k=3)
    names = [t.name for t, _ in results]
    # products should be near the top since it has a "price" column
    assert "products" in names[:2]
