from pathlib import Path

from core.evidence import unsupported_numbers, verify_claim, verify_claim_against_chunks
from core.ingestion import from_local_path
from core.rag.retriever import Retriever
from core.schemas import Chunk, SourceDocument

DOC = SourceDocument(source_id="s1", path="README.md",
                     content="# API\nThe project exposes image classification through a FastAPI endpoint.")


def test_supported_claim_has_evidence():
    c = verify_claim("The project exposes image classification through a FastAPI endpoint.", Retriever([DOC], False), [DOC])
    assert c.status == "supported" and c.evidence


def test_unrelated_claim_unsupported():
    c = verify_claim("Handles Kubernetes autoscaling across regions.", Retriever([DOC], False), [DOC])
    assert c.status == "unsupported"


def test_invented_metric_flagged():
    assert "50 ms" in unsupported_numbers("Inference takes 50 ms.", [DOC])
    c = verify_claim("FastAPI endpoint with 50 ms latency", Retriever([DOC], False), [DOC])
    assert c.status == "unsupported" and "50" in (c.note or "")


def test_local_project_fact_supported_but_inferred_limit_unsupported():
    fixture = Path(__file__).parent / "fixtures" / "tiny_counter"
    docs = from_local_path(fixture)
    retriever = Retriever(docs, use_embeddings=False)

    supported = verify_claim(
        "The counter file defaults to counter.txt in the current directory.",
        retriever,
        docs,
    )
    inferred = verify_claim(
        "State is not versioned or recoverable without backups.",
        retriever,
        docs,
    )

    assert supported.status == "supported"
    assert supported.evidence
    assert inferred.status == "unsupported"
    assert not inferred.evidence


def test_cited_chunks_can_collectively_support_a_finding():
    chunks = [
        Chunk(
            chunk_id="one",
            source_id="s1",
            path="app.js",
            text="The app uses React components.",
            start_line=1,
            end_line=1,
        ),
        Chunk(
            chunk_id="two",
            source_id="s1",
            path="index.html",
            text="The page displays a project portfolio.",
            start_line=1,
            end_line=1,
        ),
    ]

    claim = verify_claim_against_chunks(
        "The app uses React components and displays a project portfolio.",
        chunks,
    )

    assert claim.status == "supported"
    assert {e.path for e in claim.evidence} == {"app.js", "index.html"}


def test_citation_path_can_support_declared_file_format():
    chunk = Chunk(
        chunk_id="one",
        source_id="s1",
        path="app.js",
        text="const app = document.querySelector('main');",
        start_line=1,
        end_line=1,
    )

    claim = verify_claim_against_chunks("The source set includes JavaScript.", [chunk])

    assert claim.status == "supported"
    assert claim.evidence[0].path == "app.js"
