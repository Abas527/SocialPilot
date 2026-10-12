import pytest

from core import generation
from core.llm import LLMError
from core.rag.retriever import Retriever
from core.schemas import (
    EvidenceReference, GroundedFinding, ProjectProfile, SectionDraft, SourceDocument,
    TitledSectionDraft,
)

README = """# QueueKit

QueueKit is a TypeScript library for retryable background jobs. It solves the problem of
jobs failing silently when a worker crashes.

## Architecture
The library has a scheduler component and a storage adapter. The scheduler reads jobs from
the storage adapter and hands them to workers.

## Challenges
Retries caused thundering herds, so the team added jitter to the backoff delay.

## Limitations
Only an in-memory storage adapter is implemented; Redis is not supported yet.
"""
DOCS = [SourceDocument(source_id="readme", path="README.md", content=README)]


def _profile() -> ProjectProfile:
    ev = EvidenceReference(source_id="readme", path="README.md", start_line=1, end_line=4, excerpt=README[:200])
    return ProjectProfile(
        name="QueueKit",
        summary="QueueKit is a TypeScript library for retryable background jobs.",
        findings=[
            GroundedFinding(finding_id="f1", kind="summary", status="supported", evidence=[ev],
                            text="QueueKit is a TypeScript library for retryable background jobs."),
            GroundedFinding(finding_id="f2", kind="architecture", status="supported", evidence=[ev],
                            text="The library has a scheduler component and a storage adapter."),
        ],
    )


CANNED = {
    "Problem": "QueueKit solves the problem of jobs failing silently when a worker crashes.",
    "Architecture": "The library has a scheduler component and a storage adapter. The scheduler reads jobs from the storage adapter.",
    "Implementation": "QueueKit is a TypeScript library for retryable background jobs.",
    "Challenges": "Retries caused thundering herds, so jitter was added to the backoff delay.",
    "Results": "",
    "Limitations": "Only an in-memory storage adapter is implemented.",
    "Future work": "",
    "Summary": "QueueKit is a TypeScript library for retryable background jobs with a scheduler and storage adapter.",
}


def _fake(monkeypatch, canned=None, calls=None, fail=()):
    canned = canned or CANNED

    def fake_complete_json(prompt, model_cls, **kw):
        title = prompt.split('"', 2)[1]  # 'ONE section ... "Problem".'
        if calls is not None:
            calls.append(title)
        if title in fail:
            raise LLMError("model down")
        text = canned.get(title, "")
        if model_cls is TitledSectionDraft:
            return TitledSectionDraft(title="QueueKit retry design", text=text)
        return SectionDraft(text=text)

    monkeypatch.setattr(generation, "complete_json", fake_complete_json)


def _run(progress=None):
    return generation.generate_case_study_chunked(_profile(), Retriever(docs=DOCS), DOCS, "", progress)


def test_sections_are_written_one_by_one_summary_last_with_progress(monkeypatch):
    calls, ticks = [], []
    _fake(monkeypatch, calls=calls)
    cs = _run(lambda pct, label: ticks.append((pct, label)))

    assert calls[-1] == "Summary" and calls[0] == "Problem"
    assert cs.title == "QueueKit retry design"
    assert "scheduler" in cs.architecture and "jitter" in cs.challenges
    assert cs.section_status["architecture"] == "supported"
    assert cs.section_status["results"] == "skipped"  # model had nothing supported to say
    assert [pct for pct, _ in ticks] == sorted(pct for pct, _ in ticks) and ticks[-1][0] < 100
    assert ticks[0][1].startswith("Writing problem (1 of 8)")
    assert {c.section for c in cs.verified_claims} >= {"problem", "architecture", "challenges", "limitations"}
    assert cs.review_status == "preliminary_support"


def test_section_without_any_matching_material_is_skipped_without_calling_the_model(monkeypatch):
    docs = [SourceDocument(source_id="r", path="README.md", content="zzz qqq")]
    calls = []
    _fake(monkeypatch, calls=calls)
    profile = ProjectProfile(name="X", summary="")
    text, claims, status, _ = generation.write_case_study_section(
        "results", profile, Retriever(docs=docs), docs, {}, ""
    )
    assert (text, claims, status) == ("", [], "skipped") and calls == []


def test_unsupported_sentence_triggers_one_revision_and_best_version_wins(monkeypatch):
    attempts = []

    def fake(prompt, model_cls, **kw):
        attempts.append("Revise:" in prompt)
        if "Revise:" in prompt:
            return SectionDraft(text="Only an in-memory storage adapter is implemented.")
        return SectionDraft(text="Only an in-memory storage adapter is implemented. It handles ten million jobs per second.")

    monkeypatch.setattr(generation, "complete_json", fake)
    text, claims, status, _ = generation.write_case_study_section(
        "limitations", _profile(), Retriever(docs=DOCS), DOCS, {}, ""
    )
    assert attempts == [False, True]
    assert "million" not in text and status == "supported"
    assert all(c.status == "supported" for c in claims)


def test_unfixable_unsupported_claims_are_kept_but_flagged_for_review(monkeypatch):
    bad = {**CANNED, "Limitations": "Only an in-memory storage adapter is implemented. It handles ten million jobs per second."}
    _fake(monkeypatch, bad)
    cs = _run()
    assert cs.section_status["limitations"] == "needs_review"
    assert cs.review_status == "needs_review"
    assert any(c.status == "unsupported" and c.section == "limitations" for c in cs.verified_claims)
    assert "ten million" in cs.limitations  # text is preserved for the author to fix, not silently dropped


def test_one_failed_section_does_not_lose_the_others(monkeypatch):
    _fake(monkeypatch, fail={"Architecture"})
    cs = _run()
    assert cs.section_status["architecture"] == "failed" and cs.architecture == ""
    assert cs.problem and cs.limitations


def test_every_section_failing_raises(monkeypatch):
    _fake(monkeypatch, fail=set(t for t in CANNED))
    with pytest.raises(LLMError):
        _run()


def test_cancellation_from_progress_callback_propagates(monkeypatch):
    _fake(monkeypatch)

    class Stop(Exception):
        pass

    def stop(pct, label):
        raise Stop()

    with pytest.raises(Stop):
        _run(stop)


def test_regenerate_one_section_only_touches_that_section(monkeypatch):
    _fake(monkeypatch)
    cs = _run()
    before = cs.model_dump()
    _fake(monkeypatch, {**CANNED, "Challenges": "Retries caused thundering herds, so the team added jitter to the backoff delay."})
    updated = generation.regenerate_case_study_section(cs, "challenges", _profile(), Retriever(docs=DOCS), DOCS, "")
    assert updated.challenges.startswith("Retries caused thundering herds, so the team")
    assert updated.problem == before["problem"] and updated.architecture == before["architecture"]
    assert sum(1 for c in updated.verified_claims if c.section == "problem") == sum(
        1 for c in cs.verified_claims if c.section == "problem"
    )
    with pytest.raises(ValueError):
        generation.regenerate_case_study_section(cs, "title", _profile(), Retriever(docs=DOCS), DOCS, "")
