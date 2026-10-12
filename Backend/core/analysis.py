from pathlib import Path
from string import Template

from core.evidence import verify_claim_against_chunks
from core.llm import complete_json
from core.rag.retriever import Retriever
from core.schemas import Chunk, GroundedFinding, ProjectAnalysisCandidate, ProjectProfile, SourceDocument

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"

_QUERIES = [
    "what does this project do purpose problem",
    "architecture components design structure",
    "technologies frameworks libraries dependencies",
    "results metrics evaluation accuracy performance",
    "limitations challenges future work",
]
_SOURCE_FORMATS = {
    ".css": "CSS",
    ".go": "Go",
    ".html": "HTML",
    ".java": "Java",
    ".js": "JavaScript",
    ".py": "Python",
    ".rs": "Rust",
    ".ts": "TypeScript",
}


def load_prompt(name: str) -> Template:
    return Template((PROMPTS / f"{name}.txt").read_text(encoding="utf-8"))


def _analysis_chunks(retriever: Retriever) -> list[Chunk]:
    max_chunks = 12
    retrieved: dict[str, Chunk] = {}
    for q in _QUERIES:
        for h in retriever.search(q, k=4):
            retrieved.setdefault(h.chunk.chunk_id, h.chunk)
    all_by_path: dict[str, list[Chunk]] = {}
    for chunk in retriever.chunks:
        all_by_path.setdefault(chunk.path, []).append(chunk)
    chunks_by_path: dict[str, list[Chunk]] = {}
    for path, path_chunks in all_by_path.items():
        ordered = [path_chunks[0]]
        ordered.extend(
            retrieved[chunk.chunk_id]
            for chunk in path_chunks
            if chunk.chunk_id in retrieved and chunk.chunk_id != path_chunks[0].chunk_id
        )
        ordered.extend(
            chunk for chunk in path_chunks
            if chunk.chunk_id not in retrieved and chunk.chunk_id != path_chunks[0].chunk_id
        )
        chunks_by_path[path] = ordered

    selected: list[Chunk] = []
    for chunk_index in range(max((len(chunks) for chunks in chunks_by_path.values()), default=0)):
        for chunks in chunks_by_path.values():
            if chunk_index < len(chunks) and len(selected) < max_chunks:
                selected.append(chunks[chunk_index])
    return selected


def _resolve_findings(
    candidate: ProjectAnalysisCandidate,
    chunks: list[Chunk],
    docs: list[SourceDocument],
) -> list[GroundedFinding]:
    ids_by_chunk = {chunk.chunk_id: f"E{index}" for index, chunk in enumerate(chunks, start=1)}
    chunks_by_id = {ids_by_chunk[chunk.chunk_id]: chunk for chunk in chunks}
    findings: list[GroundedFinding] = []
    for index, item in enumerate(candidate.findings, start=1):
        cited_chunks = [
            chunks_by_id[evidence_id]
            for evidence_id in item.evidence_ids
            if evidence_id in chunks_by_id
        ]
        claim = verify_claim_against_chunks(item.text, cited_chunks, docs)
        note, status = claim.note, claim.status
        if any(evidence_id not in chunks_by_id for evidence_id in item.evidence_ids):
            status = "unsupported"
            note = "Finding references evidence IDs that were not provided."
        elif not cited_chunks:
            status = "unsupported"
            note = "Finding has no valid source citations."
        findings.append(GroundedFinding(
            finding_id=f"finding-{index}",
            kind=item.kind,
            text=item.text,
            evidence=claim.evidence,
            status=status,
            note=note,
        ))
    return findings


def _source_format_findings(
    retriever: Retriever,
    docs: list[SourceDocument],
    existing: list[GroundedFinding],
) -> list[GroundedFinding]:
    known_formats = {
        language
        for finding in existing
        if finding.status == "supported" and finding.kind == "technology"
        for language in _SOURCE_FORMATS.values()
        if language.casefold() in finding.text.casefold()
    }
    findings: list[GroundedFinding] = []
    for chunk in retriever.chunks:
        language = _SOURCE_FORMATS.get(Path(chunk.path).suffix.lower())
        if not language or language in known_formats:
            continue
        text = f"The project includes {language} source."
        claim = verify_claim_against_chunks(text, [chunk], docs)
        if claim.status == "supported":
            findings.append(GroundedFinding(
                finding_id=f"source-format-{len(findings) + 1}",
                kind="technology",
                text=text,
                evidence=claim.evidence,
                status="supported",
            ))
            known_formats.add(language)
    return findings


def analyze_project(
    docs: list[SourceDocument],
    retriever: Retriever,
    project_name: str | None = None,
) -> ProjectProfile:
    chunks = _analysis_chunks(retriever)
    name = project_name or (docs[0].path.split("/", 1)[0] if docs else "Imported project")
    if not chunks:
        return ProjectProfile(
            name=name,
            summary="",
            unknowns=["No source chunks were available to analyze."],
        )
    evidence_ids = {chunk.chunk_id: f"E{index}" for index, chunk in enumerate(chunks, start=1)}
    context = "\n\n---\n\n".join(
        f"[evidence_id={evidence_ids[chunk.chunk_id]}] [{chunk.path}:{chunk.start_line}-{chunk.end_line}]\n{chunk.text}"
        for chunk in chunks
    )
    prompt = load_prompt("project_analysis").substitute(context=context)
    candidate = complete_json(prompt, ProjectAnalysisCandidate)
    findings = _resolve_findings(candidate, chunks, docs)
    if findings and not any(finding.status == "supported" for finding in findings):
        correction = (
            f"{prompt}\n\nYour previous findings did not match their cited source text. "
            "Try again using only short, directly observable facts. Use the exact wording "
            "from one excerpt, cite only one to three relevant evidence IDs, and omit any "
            "fact that is not explicitly stated or shown. Do not make code-review judgments."
        )
        candidate = complete_json(correction, ProjectAnalysisCandidate)
        findings = _resolve_findings(candidate, chunks, docs)
    if not any(finding.status == "supported" for finding in findings):
        findings.extend(_source_format_findings(retriever, docs, findings))

    supported_by_kind: dict[str, list[str]] = {}
    for finding in findings:
        if finding.status == "supported":
            supported_by_kind.setdefault(finding.kind, []).append(finding.text)

    def facts(kind: str) -> list[str]:
        return supported_by_kind.get(kind, [])

    summary_facts = facts("summary") or facts("problem")
    return ProjectProfile(
        name=name,
        summary=" ".join(summary_facts),
        problem=" ".join(facts("problem")),
        technologies=facts("technology"),
        architecture=facts("architecture"),
        engineering_decisions=facts("decision"),
        challenges=facts("challenge"),
        results=facts("result"),
        limitations=facts("limitation"),
        unknowns=candidate.unknowns,
        findings=findings,
    )
