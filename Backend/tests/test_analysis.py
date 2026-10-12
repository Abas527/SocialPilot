from core import analysis
from core.rag.retriever import Retriever
from core.schemas import (
    EvidenceReference,
    FindingCandidate,
    GroundedFinding,
    ProjectAnalysisCandidate,
    ProjectProfile,
    SourceDocument,
)


DOCS = [
    SourceDocument(
        source_id="readme",
        path="README.md",
        content="# Tiny Counter\nThe counter stores its value in counter.txt and supports increment and show.",
    )
]


def test_analysis_resolves_valid_citations_and_derives_only_supported_facts(monkeypatch):
    retriever = Retriever(DOCS, use_embeddings=False)
    candidate = ProjectAnalysisCandidate(
        findings=[
            FindingCandidate(
                kind="summary",
                text="The counter stores its value in counter.txt.",
                evidence_ids=["E1"],
            ),
            FindingCandidate(
                kind="summary",
                text="The counter supports one million requests per second.",
                evidence_ids=["E1"],
            ),
            FindingCandidate(
                kind="technology",
                text="The project uses an invented framework.",
                evidence_ids=["forged:1-9"],
            ),
        ],
        unknowns=["What deployment environment is used?"],
    )
    monkeypatch.setattr(analysis, "complete_json", lambda prompt, schema: candidate)

    profile = analysis.analyze_project(DOCS, retriever, "Tiny Counter")

    assert [finding.status for finding in profile.findings] == [
        "supported",
        "unsupported",
        "unsupported",
    ]
    assert profile.summary == "The counter stores its value in counter.txt."
    assert profile.results == []
    assert profile.technologies == []
    assert profile.findings[0].evidence[0].path == "README.md"
    assert profile.unknowns == ["What deployment environment is used?"]


def test_legacy_project_profile_defaults_findings_to_empty():
    profile = ProjectProfile.model_validate({"name": "Legacy", "summary": "Old saved profile"})

    assert profile.findings == []


def test_analysis_retries_when_model_findings_fail_evidence_check(monkeypatch):
    retriever = Retriever(DOCS, use_embeddings=False)
    candidates = [
        ProjectAnalysisCandidate(
            findings=[
                FindingCandidate(
                    kind="summary",
                    text="The application improves performance across regions.",
                    evidence_ids=["E1"],
                )
            ]
        ),
        ProjectAnalysisCandidate(
            findings=[
                FindingCandidate(
                    kind="summary",
                    text="The counter stores its value in counter.txt.",
                    evidence_ids=["E1"],
                )
            ]
        ),
    ]
    prompts = []

    def fake_complete_json(prompt, schema):
        prompts.append(prompt)
        return candidates.pop(0)

    monkeypatch.setattr(analysis, "complete_json", fake_complete_json)

    profile = analysis.analyze_project(DOCS, retriever, "Tiny Counter")

    assert len(prompts) == 2
    assert "did not match their cited source text" in prompts[1]
    assert profile.summary == "The counter stores its value in counter.txt."
    assert profile.findings[0].status == "supported"


def test_analysis_falls_back_to_verifiable_file_format_facts(monkeypatch):
    docs = [
        SourceDocument(
            source_id="frontend",
            path="app.js",
            content="const button = document.querySelector('button');",
        ),
        SourceDocument(
            source_id="layout",
            path="index.html",
            content="<main>Portfolio</main>",
        ),
    ]
    candidate = ProjectAnalysisCandidate(
        findings=[
            FindingCandidate(
                kind="summary",
                text="The page provides secure authentication across regions.",
                evidence_ids=["E1"],
            )
        ]
    )
    monkeypatch.setattr(analysis, "complete_json", lambda prompt, schema: candidate)

    profile = analysis.analyze_project(docs, Retriever(docs, use_embeddings=False), "Portfolio")

    assert profile.summary == ""
    assert {finding.text for finding in profile.findings if finding.status == "supported"} == {
        "The project includes JavaScript source.",
        "The project includes HTML source.",
    }
    assert all(
        finding.evidence
        for finding in profile.findings
        if finding.status == "supported"
    )


def test_finding_evidence_exposes_only_supported_angle_relevant_sources():
    from core import generation
    from core.rag.retriever import Retriever
    from core.schemas import GroundedFinding

    def finding(finding_id, kind, text, status):
        return GroundedFinding(
            finding_id=finding_id,
            kind=kind,
            text=text,
            status=status,
            evidence=[
                EvidenceReference(
                    source_id="readme",
                    path="README.md",
                    start_line=2,
                    end_line=2,
                    excerpt=f"Source excerpt for: {text}",
                )
            ],
        )

    profile = ProjectProfile(
        name="Tiny Counter",
        summary="",
        findings=[
            finding("supported-architecture", "architecture", "The app is a CLI.", "supported"),
            finding("unsupported-decision", "decision", "It was chosen for low latency.", "unsupported"),
            finding("irrelevant-result", "result", "The app has measured throughput.", "supported"),
        ],
    )

    evidence = generation._generation_evidence(
        profile, Retriever(DOCS, use_embeddings=False), "technical_lesson"
    )

    assert "The app is a CLI." in evidence
    assert "README.md:2-2" in evidence
    assert "unsupported-decision" not in evidence
    assert "irrelevant-result" not in evidence


def test_analysis_retrieval_covers_opening_chunks_across_source_files():
    docs = [
        SourceDocument(source_id=name, path=f"{name}.js", content=f"{name}\n" * 700)
        for name in ("alpha", "bravo", "charlie")
    ]
    chunks = analysis._analysis_chunks(Retriever(docs, use_embeddings=False))

    assert len(chunks) <= 12
    assert [chunk.path for chunk in chunks[:3]] == [
        "alpha.js",
        "bravo.js",
        "charlie.js",
    ]
