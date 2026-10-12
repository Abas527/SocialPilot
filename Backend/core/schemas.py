from typing import Literal
from pydantic import BaseModel, Field


class SourceDocument(BaseModel):
    source_id: str
    path: str
    content: str
    source_url: str | None = None
    commit_sha: str | None = None


class Chunk(BaseModel):
    chunk_id: str
    source_id: str
    path: str
    text: str
    start_line: int
    end_line: int
    heading: str | None = None
    source_url: str | None = None


FindingKind = Literal[
    "summary", "problem", "technology", "architecture", "decision",
    "challenge", "result", "limitation",
]


class EvidenceReference(BaseModel):
    source_id: str
    path: str
    start_line: int | None = None
    end_line: int | None = None
    source_url: str | None = None
    excerpt: str


ClaimStatus = Literal["supported", "needs_review", "unsupported"]
DraftReviewStatus = Literal["needs_review", "preliminary_support"]


class Claim(BaseModel):
    section: str | None = None  # which case-study section the claim belongs to
    text: str
    evidence: list[EvidenceReference] = Field(default_factory=list)
    status: ClaimStatus = "needs_review"
    note: str | None = None


class GroundedFinding(BaseModel):
    finding_id: str
    kind: FindingKind
    text: str
    evidence: list[EvidenceReference] = Field(default_factory=list)
    status: ClaimStatus = "needs_review"
    note: str | None = None


AnalysisFindingKind = Literal["summary", "technology", "architecture", "decision"]


class FindingCandidate(BaseModel):
    kind: AnalysisFindingKind
    text: str
    evidence_ids: list[str] = Field(min_length=1, max_length=3)


class ProjectAnalysisCandidate(BaseModel):
    findings: list[FindingCandidate] = Field(min_length=1)
    unknowns: list[str] = Field(default_factory=list)


class ProjectProfile(BaseModel):
    name: str
    summary: str
    problem: str = ""
    target_users: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    architecture: list[str] = Field(default_factory=list)
    engineering_decisions: list[str] = Field(default_factory=list)
    challenges: list[str] = Field(default_factory=list)
    results: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    findings: list[GroundedFinding] = Field(default_factory=list)


Angle = Literal["technical_lesson", "engineering_decision", "personal_reflection"]


class LinkedInDraft(BaseModel):
    angle: Angle
    hook: str
    insight: str
    body: str
    takeaway: str
    question: str | None = None
    needs_user_input: str | None = None  # e.g. personal reflection missing context
    claims: list[str] = Field(default_factory=list)  # raw claim texts from the LLM
    verified_claims: list[Claim] = Field(default_factory=list)  # filled by evidence.py
    review_status: DraftReviewStatus = "needs_review"


class CaseStudy(BaseModel):
    title: str
    summary: str
    problem: str
    architecture: str
    implementation: str
    challenges: str
    results: str
    limitations: str
    future_work: str
    claims: list[str] = Field(default_factory=list)
    verified_claims: list[Claim] = Field(default_factory=list)
    review_status: DraftReviewStatus = "needs_review"
    # Chunked generation: per-section outcome ("supported" | "needs_review" |
    # "skipped" (no evidence) | "failed"). Empty for single-shot case studies.
    section_status: dict[str, str] = Field(default_factory=dict)


class SectionDraft(BaseModel):
    """One case-study section written on its own (small prompts suit small models)."""
    text: str = ""
    claims: list[str] = Field(default_factory=list)


class TitledSectionDraft(SectionDraft):
    title: str = ""


class CommunityPost(BaseModel):
    """A developer-community post grounded in the project's evidence."""
    body: str
    tags: list[str] = Field(default_factory=list)
    needs_user_input: str | None = None
    claims: list[str] = Field(default_factory=list)
    verified_claims: list[Claim] = Field(default_factory=list)
    review_status: DraftReviewStatus = "needs_review"
