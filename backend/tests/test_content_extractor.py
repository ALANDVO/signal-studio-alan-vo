from app.services.content_extractor import (
    extract_content,
    chunk_fast_text,
    chunk_structured_markdown,
    chunk_semantic_sliding,
    search_knowledge_chunks,
)


def test_chunk_fast_text_splits_by_paragraphs():
    doc = "First paragraph of content.\n\nSecond paragraph of information.\n\nThird paragraph."
    chunks = chunk_fast_text(doc, max_words=50)
    assert len(chunks) >= 1
    assert all(c["metadata"]["strategy"] == "fast_text" for c in chunks)


def test_chunk_structured_markdown_preserves_headings():
    doc = """# Introduction
Welcome to the documentation.

## Installation
Run pip install.

## Quickstart
Execute the main script.
"""
    chunks = chunk_structured_markdown(doc)
    assert len(chunks) >= 2
    headings = [c["heading"] for c in chunks]
    assert "Installation" in headings or "Quickstart" in headings


def test_chunk_semantic_sliding_window_overlap():
    doc = "Sentence one is here. Sentence two follows it. Sentence three comes next. Sentence four is also present. Sentence five concludes."
    chunks = chunk_semantic_sliding(doc, window_words=8, overlap_words=4)
    assert len(chunks) >= 2
    assert chunks[0]["metadata"]["strategy"] == "semantic_chunks"


def test_search_knowledge_chunks_bm25_ranking():
    chunks = [
        {"id": "c1", "text": "Deep learning models use gradient descent.", "heading": "Optimization"},
        {"id": "c2", "text": "Kubernetes manages containerized workloads.", "heading": "DevOps"},
    ]
    results = search_knowledge_chunks(chunks, "gradient descent optimization", limit=2)
    assert len(results) > 0
    assert results[0]["id"] == "c1"
    assert results[0]["score"] > 0
