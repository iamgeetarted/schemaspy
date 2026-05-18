"""Pure Python TF-IDF cosine similarity for semantic table/column search."""

from __future__ import annotations

import math
import re
from collections import Counter

from schemaspy.models import TableInfo


def _tokenize(text: str) -> list[str]:
    """Lowercase and split on non-alphabetic characters."""
    return [tok for tok in re.split(r"[^a-z]+", text.lower()) if tok]


def _idf(docs: list[list[str]]) -> dict[str, float]:
    """Compute inverse document frequency for all terms across docs."""
    n = len(docs)
    if n == 0:
        return {}
    df: dict[str, int] = {}
    for doc in docs:
        for term in set(doc):
            df[term] = df.get(term, 0) + 1
    return {term: math.log((n + 1) / (count + 1)) + 1.0 for term, count in df.items()}


def _tfidf_vec(tokens: list[str], idf: dict[str, float], vocab: list[str]) -> list[float]:
    """Build a TF-IDF vector aligned to vocab."""
    if not tokens:
        return [0.0] * len(vocab)
    tf = Counter(tokens)
    total = len(tokens)
    vec = []
    for term in vocab:
        tf_val = tf.get(term, 0) / total
        idf_val = idf.get(term, 0.0)
        vec.append(tf_val * idf_val)
    return vec


def _cosine(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(y * y for y in b))
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot / (mag_a * mag_b)


def _table_text(table: TableInfo) -> str:
    """Build a text representation of a table for similarity comparison."""
    parts = [table.name]
    for col in table.columns:
        parts.append(col.name)
        parts.append(col.type)
    for fk in table.foreign_keys:
        parts.append(fk.ref_table)
    return " ".join(parts)


def find_similar_tables(
    query: str, tables: list[TableInfo], top_k: int = 5
) -> list[tuple[TableInfo, float]]:
    """
    Find the top_k tables most semantically similar to the query string
    using TF-IDF cosine similarity.
    """
    if not tables:
        return []

    # Build corpus: query doc + table docs
    table_texts = [_table_text(t) for t in tables]
    query_tokens = _tokenize(query)
    table_token_lists = [_tokenize(text) for text in table_texts]

    all_docs = [query_tokens] + table_token_lists
    idf = _idf(all_docs)

    # Vocabulary: union of all terms
    vocab = list(idf.keys())

    query_vec = _tfidf_vec(query_tokens, idf, vocab)
    scores: list[tuple[TableInfo, float]] = []
    for table, tokens in zip(tables, table_token_lists):
        table_vec = _tfidf_vec(tokens, idf, vocab)
        score = _cosine(query_vec, table_vec)
        scores.append((table, score))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:top_k]
