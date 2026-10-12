"""Deterministic claim checking against retrieved chunks.
Statuses are PRELIMINARY: lexical support, not proof of truth. Excerpts stay visible for the user."""
import re
from collections.abc import Iterable

from core.rag.bm25 import tokenize
from core.rag.retriever import Retriever
from core.schemas import Chunk, Claim, EvidenceReference, SourceDocument

_STOP = set(
    "the a an and or of to in on for with is are was were be by as at it this that from its their can "
    "source sources set project projects code codebase snippets provided includes include contains".split()
)
_NUM = re.compile(r"\b\d+(?:\.\d+)?\s?(?:%|ms|s|x|k|m|users|requests|rps)?", re.I)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])|[\r\n]+|;\s+")
SUPPORTED, REVIEW = 0.6, 0.3
_PATH_FACTS = {
    ".js": {"javascript"},
    ".ts": {"typescript"},
    ".py": {"python"},
    ".html": {"html"},
    ".css": {"css"},
    ".go": {"go"},
    ".rs": {"rust"},
    ".java": {"java"},
}


def _terms(text: str) -> set[str]:
    return {t for t in tokenize(text) if t not in _STOP and len(t) > 2}


def _chunk_terms(chunk: Chunk) -> set[str]:
    extension = f".{chunk.path.rsplit('.', 1)[-1].lower()}" if "." in chunk.path else ""
    return _terms(f"{chunk.path} {chunk.text}") | _PATH_FACTS.get(extension, set())


def verify_claim(text: str, retriever: Retriever, docs: list[SourceDocument] | None = None) -> Claim:
    terms = _terms(text)
    best, best_cov = [], 0.0
    for hit in retriever.search(text, k=3):
        cov = len(terms & _terms(hit.chunk.text)) / len(terms) if terms else 0.0
        if cov > 0:
            best.append((cov, hit.chunk))
        best_cov = max(best_cov, cov)
    evidence = [
        EvidenceReference(
            source_id=c.source_id, path=c.path, start_line=c.start_line, end_line=c.end_line,
            source_url=c.source_url, excerpt=c.text[:400],
        )
        for cov, c in sorted(best, key=lambda x: -x[0])[:2]
    ]
    status = "supported" if best_cov >= SUPPORTED else "needs_review" if best_cov >= REVIEW else "unsupported"
    note = None
    if docs:
        missing = unsupported_numbers(text, docs)
        if missing:
            status, note = "unsupported", f"Numbers not found in sources: {', '.join(missing)}"
    return Claim(text=text, evidence=evidence if status != "unsupported" else [], status=status, note=note)


def unsupported_numbers(text: str, docs: list[SourceDocument]) -> list[str]:
    """Flag invented metrics: any number in generated text that never appears in the sources."""
    corpus = " ".join(d.content for d in docs)
    return sorted({m.group().strip() for m in _NUM.finditer(text)
                   if len(m.group().strip()) > 1 and m.group().strip() not in corpus})


def verify_claims(claims: list[str], retriever: Retriever, docs: list[SourceDocument] | None = None) -> list[Claim]:
    return [verify_claim(c, retriever, docs) for c in claims if c.strip()]


def verify_claim_against_chunks(
    text: str,
    chunks: list[Chunk],
    docs: list[SourceDocument] | None = None,
) -> Claim:
    terms = _terms(text)
    scored = [
        (len(terms & _chunk_terms(chunk)) / len(terms), chunk)
        for chunk in chunks
    ] if terms else []
    cited_terms = set().union(*(_chunk_terms(chunk) for chunk in chunks)) if chunks else set()
    best_cov = len(terms & cited_terms) / len(terms) if terms else 0.0
    status = "supported" if best_cov >= SUPPORTED else "needs_review" if best_cov >= REVIEW else "unsupported"
    evidence = [
        EvidenceReference(
            source_id=chunk.source_id,
            path=chunk.path,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
            source_url=chunk.source_url,
            excerpt=chunk.text[:400],
        )
        for coverage, chunk in sorted(scored, key=lambda item: item[0], reverse=True)[:3]
        if coverage > 0
    ]
    note = None
    if docs:
        missing = unsupported_numbers(text, docs)
        if missing:
            status = "unsupported"
            note = f"Numbers not found in sources: {', '.join(missing)}"
    return Claim(
        text=text,
        evidence=evidence if status != "unsupported" else [],
        status=status,
        note=note,
    )


def draft_statements(fields: Iterable[str], model_claims: list[str]) -> list[str]:
    """Collect prose statements and model-listed claims without trusting the model list."""
    statements: list[str] = []
    seen: set[str] = set()
    for text in [*fields, *model_claims]:
        for statement in _SENTENCE_SPLIT.split(text):
            statement = re.sub(r"^\s*(?:[-*•]\s*|\d+[.)]\s*)", "", statement).strip()
            if not statement:
                continue
            key = " ".join(statement.casefold().split())
            if key not in seen:
                seen.add(key)
                statements.append(statement)
    return statements
