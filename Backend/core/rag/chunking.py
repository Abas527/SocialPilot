"""Line-aware chunking so every chunk maps back to a file + line range (needed for evidence)."""
import re

from core.schemas import Chunk, SourceDocument

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")


def chunk_document(doc: SourceDocument, max_chars: int = 1200) -> list[Chunk]:
    lines = doc.content.splitlines()
    chunks: list[Chunk] = []
    buf: list[str] = []
    start = 1
    heading: str | None = None
    buf_heading: str | None = None
    size = 0

    def flush(end_line: int) -> None:
        nonlocal buf, size, start, buf_heading
        text = "\n".join(buf).strip()
        if text:
            chunks.append(Chunk(
                chunk_id=f"{doc.source_id}:{start}-{end_line}", source_id=doc.source_id,
                path=doc.path, text=text, start_line=start, end_line=end_line,
                heading=buf_heading, source_url=doc.source_url,
            ))
        buf, size = [], 0
        start = end_line + 1
        buf_heading = heading

    for i, line in enumerate(lines, start=1):
        m = _HEADING.match(line)
        if m:
            if buf:
                flush(i - 1)
            heading = m.group(2).strip()
            buf_heading = heading
        if not buf:
            buf_heading = heading
        buf.append(line)
        size += len(line) + 1
        if size >= max_chars:
            flush(i)
    if buf:
        flush(len(lines))
    return chunks


def chunk_documents(docs: list[SourceDocument], max_chars: int = 1200) -> list[Chunk]:
    return [c for d in docs for c in chunk_document(d, max_chars)]
