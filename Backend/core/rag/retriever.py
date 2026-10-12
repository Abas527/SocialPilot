"""Hybrid retriever: BM25 always, embeddings optionally, fused with Reciprocal Rank Fusion."""
from dataclasses import dataclass

from config import settings
from core.rag.bm25 import BM25
from core.rag.chunking import chunk_documents
from core.schemas import Chunk, SourceDocument


@dataclass
class Hit:
    chunk: Chunk
    score: float


class Retriever:
    def __init__(
        self,
        docs: list[SourceDocument] | None = None,
        use_embeddings: bool | None = None,
        *,
        chunks: list[Chunk] | None = None,
    ):
        if chunks is not None:
            self.chunks = chunks
        elif docs is not None:
            self.chunks = chunk_documents(docs, settings.chunk_chars)
        else:
            raise ValueError("Provide source documents or persisted chunks.")
        self.bm25 = BM25([c.text for c in self.chunks])
        self.use_embeddings = settings.use_embeddings if use_embeddings is None else use_embeddings
        self._vecs: list[list[float]] | None = None

    def _dense_ranking(self, query: str) -> list[int]:
        from core.rag.embeddings import cosine, embed  # lazy: only when enabled
        if self._vecs is None:
            self._vecs = [embed(c.text) for c in self.chunks]
        q = embed(query)
        sims = [cosine(q, v) for v in self._vecs]
        return sorted(range(len(sims)), key=lambda i: -sims[i])

    def search(self, query: str, k: int | None = None) -> list[Hit]:
        k = k or settings.top_k
        if not self.chunks:
            return []
        sparse = self.bm25.scores(query)
        rankings = [sorted(range(len(sparse)), key=lambda i: -sparse[i])]
        if self.use_embeddings:
            try:
                rankings.append(self._dense_ranking(query))
            except Exception:
                pass  # degrade gracefully to BM25-only
        fused: dict[int, float] = {}
        for ranking in rankings:
            for rank, idx in enumerate(ranking):
                fused[idx] = fused.get(idx, 0.0) + 1.0 / (60 + rank)
        top = sorted(fused, key=lambda i: -fused[i])[:k]
        # drop chunks with zero lexical signal when running BM25-only
        return [Hit(self.chunks[i], fused[i]) for i in top if sparse[i] > 0 or self.use_embeddings]

    def context_for(self, query: str, k: int | None = None) -> str:
        """Formatted, source-labelled context block to inject into prompts."""
        parts = []
        for h in self.search(query, k):
            c = h.chunk
            parts.append(f"[{c.path}:{c.start_line}-{c.end_line}]\n{c.text}")
        return "\n\n---\n\n".join(parts)
