from core.rag.chunking import chunk_document
from core.rag.retriever import Retriever
from core.schemas import SourceDocument

README = """# Image API
Serves image classification through a FastAPI endpoint.

## Setup
Install with pip and run uvicorn.

## Limitations
No latency benchmarks have been published.
"""


def doc():
    return SourceDocument(source_id="s1", path="README.md", content=README)


def test_chunks_have_line_ranges_and_headings():
    chunks = chunk_document(doc(), max_chars=80)
    assert chunks and all(c.start_line <= c.end_line for c in chunks)
    assert any(c.heading == "Limitations" for c in chunks)


def test_retrieval_finds_relevant_chunk():
    r = Retriever([doc()], use_embeddings=False)
    hits = r.search("FastAPI classification endpoint")
    assert hits and "FastAPI" in hits[0].chunk.text
    assert r.search("zzzz qqqq") == []
