from core import generation
from core.rag.retriever import Retriever
from core.schemas import (
    EvidenceReference,
    GroundedFinding,
    LinkedInDraft,
    ProjectProfile,
    SourceDocument,
)


DOCS = [
    SourceDocument(
        source_id="counter",
        path="README.md",
        content="Tiny Counter stores a count in counter.txt and supports increment and show.",
    )
]
PROFILE = ProjectProfile(name="Tiny Counter", summary="A counter stored in a text file.")

PROFILE.findings = [
    GroundedFinding(
        finding_id="counter-storage",
        kind="architecture",
        text="Tiny Counter stores a count in counter.txt.",
        status="supported",
        evidence=[
            EvidenceReference(
                source_id="counter",
                path="README.md",
                start_line=1,
                end_line=1,
                excerpt=DOCS[0].content,
            )
        ],
    ),
    GroundedFinding(
        finding_id="counter-choice",
        kind="decision",
        text="Tiny Counter stores a count in counter.txt.",
        status="supported",
        evidence=[
            EvidenceReference(
                source_id="counter",
                path="README.md",
                start_line=1,
                end_line=1,
                excerpt=DOCS[0].content,
            )
        ],
    ),
]


def test_empty_linkedin_draft_is_retried(monkeypatch):
    responses = [
        LinkedInDraft(angle="engineering_decision", hook="", insight="", body="", takeaway=""),
        LinkedInDraft(
            angle="engineering_decision",
            hook="Tiny Counter stores its count in a text file.",
            insight="",
            body="The counter supports increment and show operations.",
            takeaway="",
            claims=[
                "Tiny Counter stores its count in a text file.",
                "The counter supports increment and show operations.",
            ],
        ),
    ]
    prompts = []

    def fake_complete_json(prompt, model_cls):
        prompts.append(prompt)
        return responses.pop(0)

    monkeypatch.setattr(generation, "complete_json", fake_complete_json)

    draft = generation.generate_linkedin_draft(
        PROFILE, Retriever(DOCS, use_embeddings=False), DOCS, "engineering_decision"
    )

    assert len(prompts) == 2
    assert "Excerpt: Tiny Counter stores a count in counter.txt" in prompts[0]
    assert "did not include a post body" in prompts[1]
    assert draft.hook == "Tiny Counter stores its count in a text file."


def test_personal_reflection_without_context_requires_user_input(monkeypatch):
    def should_not_generate(prompt, model_cls):
        raise AssertionError("Do not invent personal reflection without user context.")

    monkeypatch.setattr(generation, "complete_json", should_not_generate)

    draft = generation.generate_linkedin_draft(
        PROFILE, Retriever(DOCS, use_embeddings=False), DOCS, "personal_reflection"
    )

    assert draft.hook == ""
    assert draft.needs_user_input
    assert "personal experience or lesson" in draft.needs_user_input


def test_generated_linkedin_prose_is_preserved_and_flagged_for_review(monkeypatch):
    monkeypatch.setattr(
        generation,
        "complete_json",
        lambda prompt, model_cls: LinkedInDraft(
            angle="technical_lesson",
            hook="Tiny Counter stores a count in counter.txt.",
            insight="",
            body="It reduces latency by 15%.",
            takeaway="",
            claims=[],
        ),
    )

    draft = generation.generate_linkedin_draft(
        PROFILE, Retriever(DOCS, use_embeddings=False), DOCS, "technical_lesson"
    )

    assert "15%" in draft.body
    assert [claim.status for claim in draft.verified_claims] == ["supported", "unsupported"]
    assert draft.review_status == "needs_review"


def test_all_supported_draft_statements_are_labeled_preliminary(monkeypatch):
    monkeypatch.setattr(
        generation,
        "complete_json",
        lambda prompt, model_cls: LinkedInDraft(
            angle="technical_lesson",
            hook="Tiny Counter stores a count in counter.txt.",
            insight="",
            body="Tiny Counter supports increment and show.",
            takeaway="",
            claims=[],
        ),
    )

    draft = generation.generate_linkedin_draft(
        PROFILE, Retriever(DOCS, use_embeddings=False), DOCS, "technical_lesson"
    )

    assert draft.verified_claims[0].status == "supported"
    assert draft.review_status == "preliminary_support"


def test_no_supported_findings_prevents_generation_without_legacy_fallback(monkeypatch):
    profile = ProjectProfile(
        name="Tiny Counter",
        summary="A counter stored in a text file.",
        findings=[
            GroundedFinding(
                finding_id="finding-1",
                kind="summary",
                text="A counter stores a value.",
                status="unsupported",
                evidence=[],
            )
        ],
    )

    def should_not_generate(prompt, model_cls):
        raise AssertionError("No unsupported/raw-source fallback is permitted.")

    monkeypatch.setattr(generation, "complete_json", should_not_generate)

    try:
        generation.generate_linkedin_draft(
            profile, Retriever(DOCS, use_embeddings=False), DOCS, "technical_lesson"
        )
    except generation.LLMError as exc:
        assert "No source-backed findings" in str(exc)
    else:
        raise AssertionError("Generation must stop when no eligible finding is supported.")


def test_engineering_decision_requires_a_supported_decision_finding(monkeypatch):
    profile = ProjectProfile(
        name="Tiny Counter",
        summary="",
        findings=PROFILE.findings[:1],
    )

    def should_not_generate(prompt, model_cls):
        raise AssertionError("Technical facts are not decision evidence.")

    monkeypatch.setattr(generation, "complete_json", should_not_generate)

    try:
        generation.generate_linkedin_draft(
            profile, Retriever(DOCS, use_embeddings=False), DOCS, "engineering_decision"
        )
    except generation.LLMError as exc:
        assert "No source-backed findings" in str(exc)
    else:
        raise AssertionError("Decision drafts require a documented decision finding.")


def test_case_study_preserves_generated_prose_and_flags_unverified_claims(monkeypatch):
    profile = ProjectProfile(
        name="Tiny Counter",
        summary="A counter stored in a text file.",
        findings=[
            GroundedFinding(
                finding_id="supported",
                kind="summary",
                text="Tiny Counter stores a count in counter.txt.",
                status="supported",
                evidence=[
                    EvidenceReference(
                        source_id="counter",
                        path="README.md",
                        start_line=1,
                        end_line=1,
                        excerpt=DOCS[0].content,
                    )
                ],
            ),
            GroundedFinding(
                finding_id="unsupported",
                kind="result",
                text="Tiny Counter serves one million requests per second.",
                status="unsupported",
            ),
        ],
    )
    prompts = []

    def fake_complete_json(prompt, model_cls):
        prompts.append(prompt)
        return generation.CaseStudy(
            title="Tiny Counter",
            summary="Tiny Counter stores a count in counter.txt.",
            problem="",
            architecture="",
            implementation="",
            challenges="",
            results="It serves one million requests per second.",
            limitations="",
            future_work="",
        )

    monkeypatch.setattr(generation, "complete_json", fake_complete_json)

    case_study = generation.generate_case_study(
        profile, Retriever(DOCS, use_embeddings=False), DOCS
    )

    assert "Tiny Counter serves one million requests per second." not in prompts[0]
    assert "Excerpt: Tiny Counter stores a count in counter.txt" in prompts[0]
    assert "supported" in prompts[0]
    assert case_study.results == "It serves one million requests per second."
    assert [claim.status for claim in case_study.verified_claims] == [
        "supported",
        "unsupported",
    ]
    assert case_study.review_status == "needs_review"


def test_case_study_retries_when_model_omits_the_executive_summary(monkeypatch):
    prompts = []
    responses = [
        generation.CaseStudy(
            title="Tiny Counter",
            summary="",
            problem="",
            architecture="The counter stores its value in a text file.",
            implementation="",
            challenges="",
            results="",
            limitations="",
            future_work="",
        ),
        generation.CaseStudy(
            title="Tiny Counter",
            summary="Tiny Counter stores a count in counter.txt.",
            problem="",
            architecture="",
            implementation="",
            challenges="",
            results="",
            limitations="",
            future_work="",
        ),
    ]

    def fake_complete_json(prompt, model_cls):
        prompts.append(prompt)
        return responses.pop(0)

    monkeypatch.setattr(generation, "complete_json", fake_complete_json)

    case_study = generation.generate_case_study(
        PROFILE, Retriever(DOCS, use_embeddings=False), DOCS
    )

    assert len(prompts) == 2
    assert "no executive summary" in prompts[1]
    assert case_study.summary == "Tiny Counter stores a count in counter.txt."
