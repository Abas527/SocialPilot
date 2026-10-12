"""Verifiable publications: what an author published + the evidence behind it.

When a case study or post is published we freeze (a) the exact text, (b) every
sentence of it re-checked against the author's sources, (c) the evidence excerpts
with commit-pinned GitHub permalinks, and (d) a SHA-256 of the text. A public,
no-login endpoint exposes this so a reader (e.g. a recruiter) can inspect it and,
for GitHub projects, re-verify the excerpts directly against GitHub.

Honesty note: the check is lexical (keyword coverage + "numbers must exist in the
sources"). It shows WHERE a statement comes from; it does not prove it is true.
"""
import hashlib
import json
import re
import secrets
import uuid
from urllib.parse import quote

import httpx

from core import pipeline, storage
from core.evidence import draft_statements, verify_claims
from core.ingestion import IngestionError, parse_github_url

METHOD = (
    "Each sentence is matched to excerpts of the author's project sources by keyword "
    "overlap (BM25 retrieval plus term coverage), and any number must appear in the "
    "sources. This shows where a statement comes from; it does not prove it is true."
)
CASE_SECTIONS = (
    "summary", "problem", "architecture", "implementation",
    "challenges", "results", "limitations", "future_work",
)
OWNERSHIP_FILE = ".socialpilot-verify"
_SHA = re.compile(r"^[0-9a-f]{40}$")
_SAFE_PATH = re.compile(r"^[A-Za-z0-9_@+.\- /]+$")
MAX_REVERIFY_FILES = 12


class PublicationError(ValueError):
    pass


# ------------------------------------------------------------------ claim building

_FENCE = re.compile(r"```.*?```", re.DOTALL)
_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")


def _prose_statements(text: str) -> list[str]:
    """Checkable sentences of a Markdown/plain text (no code, headings or questions)."""
    text = _FENCE.sub(" ", text)
    text = _LINK.sub(r"\1", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"[*_`>]+", "", text)
    out = []
    for sentence in draft_statements((text,), []):
        if len(sentence.split()) >= 4 and not sentence.rstrip().endswith("?"):
            out.append(sentence)
    return out


def _permalink(source_url: str | None, start: int | None, end: int | None) -> str | None:
    if not source_url:
        return None
    if start is None:
        return source_url
    return f"{source_url}#L{start}" + (f"-L{end}" if end and end != start else "")


def _build_claims(texts: dict[str, str], retriever, docs) -> list[dict]:
    claims: list[dict] = []
    for section, text in texts.items():
        for claim in verify_claims(_prose_statements(text), retriever, docs):
            claims.append({
                "section": section,
                "text": claim.text,
                "status": claim.status,
                "note": claim.note,
                "evidence": [
                    {
                        "path": e.path,
                        "start_line": e.start_line,
                        "end_line": e.end_line,
                        "excerpt": e.excerpt,
                        "source_url": e.source_url,
                        "permalink": _permalink(e.source_url, e.start_line, e.end_line),
                    }
                    for e in claim.evidence
                ],
            })
    return claims


def _manifest(claims: list[dict], docs) -> list[dict]:
    by_path = {d.path: d for d in docs}
    seen, out = set(), []
    for claim in claims:
        for ev in claim["evidence"]:
            if ev["path"] in seen or ev["path"] not in by_path:
                continue
            seen.add(ev["path"])
            d = by_path[ev["path"]]
            out.append({
                "path": d.path,
                "source_url": d.source_url,
                "commit_sha": d.commit_sha,
                "sha256": hashlib.sha256(d.content.encode("utf-8")).hexdigest(),
            })
    return out


def content_hash(content: dict) -> str:
    canonical = json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------- creation

def _owned_project(user_id: str, project_id: str):
    owner = storage.get_project_owner(project_id)
    if owner is None or owner["user_id"] != user_id:
        raise KeyError("Project not found.")
    return pipeline._load(project_id)  # (project, docs, retriever)


def _create(user_id, project, docs, retriever, kind, artifact_type, title, content, texts) -> dict:
    claims = _build_claims(texts, retriever, docs)
    supported = sum(1 for c in claims if c["status"] == "supported")
    has_repo = bool(project.get("repository_url") and project.get("commit_sha"))
    ownership = ownership_status(project["project_id"])
    publication_id = uuid.uuid4().hex
    with storage.conn() as c:
        c.execute(
            """INSERT INTO publications(publication_id,user_id,project_id,kind,artifact_type,
            title,content_json,content_sha256,trust_level,repository_url,commit_sha,
            ownership_verified,claims_json,sources_json,supported,total,method,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                publication_id, user_id, project["project_id"], kind, artifact_type, title,
                json.dumps(content, ensure_ascii=False), content_hash(content),
                "repository" if has_repo else "notes",
                project.get("repository_url"), project.get("commit_sha"),
                1 if (has_repo and ownership["verified"]) else 0,
                json.dumps(claims, ensure_ascii=False),
                json.dumps(_manifest(claims, docs), ensure_ascii=False),
                supported, len(claims), METHOD, storage._now(),
            ),
        )
    return {"publication_id": publication_id, "supported": supported, "total": len(claims),
            "trust_level": "repository" if has_repo else "notes",
            "ownership_verified": bool(has_repo and ownership["verified"])}


def publish_case_study(user_id: str, project_id: str) -> dict:
    """Snapshot the project's current case study (edited version wins) with fresh evidence."""
    project, docs, retriever = _owned_project(user_id, project_id)
    artifact = storage.get_project_artifact(project_id, "case_study")
    if artifact is None:
        raise PublicationError("Generate the case study before publishing it.")
    current = artifact["current"]
    texts = {s: (current.get(s) or "").strip() for s in CASE_SECTIONS}
    texts = {s: t for s, t in texts.items() if t}
    if not texts:
        raise PublicationError("The case study has no content to publish.")
    title = (current.get("title") or project["name"]).strip()
    content = {"title": title, **{s: texts.get(s, "") for s in CASE_SECTIONS}}
    return _create(user_id, project, docs, retriever, "case_study", "case_study", title, content, texts)


def publish_post_text(user_id: str, project_id: str, body: str, artifact_type: str | None = None) -> dict:
    """Snapshot post text the author is about to publish, checked against their project."""
    project, docs, retriever = _owned_project(user_id, project_id)
    return _create(user_id, project, docs, retriever, "post", artifact_type, "", {"body": body},
                   {"body": body})


# ------------------------------------------------------------------- reading

def _row(publication_id: str):
    with storage.conn() as c:
        row = c.execute(
            """SELECT p.*,u.username,u.display_name FROM publications p
            JOIN users u ON u.user_id=p.user_id WHERE p.publication_id=?""",
            (publication_id,),
        ).fetchone()
    if row is None:
        raise KeyError("Publication not found.")
    return row


def _repo(url: str | None, sha: str | None) -> dict | None:
    if not url:
        return None
    try:
        owner, name = parse_github_url(url)
    except IngestionError:
        return None
    base = f"https://github.com/{owner}/{name}"
    return {"url": base, "owner": owner, "name": name, "commit_sha": sha,
            "commit_url": f"{base}/commit/{sha}" if sha else None}


def get_public(publication_id: str) -> dict:
    """Everything a stranger needs to judge a publication. No private ids are exposed."""
    row = _row(publication_id)
    if row["revoked_at"]:
        raise PublicationError("This publication was unpublished by its author.")
    content = json.loads(row["content_json"])
    claims = json.loads(row["claims_json"])
    notes = row["trust_level"] == "notes"
    return {
        "publication_id": row["publication_id"],
        "kind": row["kind"],
        "title": row["title"],
        "created_at": row["created_at"],
        "author": {"username": row["username"], "display_name": row["display_name"]},
        "content": content,
        "trust": {
            "level": row["trust_level"],
            "label": (
                "Self-reported: written from the author's own notes, so it cannot be "
                "independently checked."
                if notes else
                "Repository-backed: claims link to exact lines in a public GitHub repository "
                "at a fixed commit."
            ),
            "repository": None if notes else _repo(row["repository_url"], row["commit_sha"]),
            "ownership_verified": bool(row["ownership_verified"]),
            "supported": row["supported"],
            "total": row["total"],
            "method": row["method"],
        },
        "claims": claims,
        "sources": json.loads(row["sources_json"]),
        "integrity": {
            "algorithm": "sha256 over canonical JSON (sorted keys, compact, UTF-8)",
            "content_sha256": row["content_sha256"],
            "intact": content_hash(content) == row["content_sha256"],
        },
    }


def list_for_project(user_id: str, project_id: str) -> list[dict]:
    with storage.conn() as c:
        rows = c.execute(
            """SELECT publication_id,kind,title,supported,total,trust_level,ownership_verified,
            created_at,revoked_at FROM publications WHERE user_id=? AND project_id=?
            ORDER BY created_at DESC LIMIT 50""",
            (user_id, project_id),
        ).fetchall()
    return [{**dict(r), "ownership_verified": bool(r["ownership_verified"]),
             "revoked": r["revoked_at"] is not None} for r in rows]


def revoke(user_id: str, publication_id: str) -> bool:
    """Unpublish: the public page stops working and feed posts that point at it are removed."""
    with storage.conn() as c:
        cursor = c.execute(
            "UPDATE publications SET revoked_at=? WHERE publication_id=? AND user_id=? AND revoked_at IS NULL",
            (storage._now(), publication_id, user_id),
        )
        if cursor.rowcount:
            c.execute("DELETE FROM social_posts WHERE publication_id=? AND user_id=?",
                      (publication_id, user_id))
    return cursor.rowcount > 0


# ------------------------------------------------------------ independent re-check

def _norm(text: str) -> str:
    return " ".join(text.split())


def _raw_url(owner: str, repo: str, sha: str, path: str) -> str:
    if not _SHA.fullmatch(sha) or ".." in path.split("/") or path.startswith("/") or not _SAFE_PATH.fullmatch(path):
        raise PublicationError("Unsafe evidence path.")
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{sha}/{quote(path)}"


def reverify(publication_id: str) -> dict:
    """Re-fetch the cited files straight from GitHub and confirm each excerpt is really there."""
    row = _row(publication_id)
    if row["revoked_at"]:
        raise PublicationError("This publication was unpublished by its author.")
    if row["trust_level"] != "repository" or not row["commit_sha"]:
        raise PublicationError("Only repository-backed publications can be re-verified.")
    repo = _repo(row["repository_url"], row["commit_sha"])
    if repo is None:
        raise PublicationError("The repository could not be identified.")
    claims = json.loads(row["claims_json"])
    manifest = {m["path"]: m for m in json.loads(row["sources_json"])}
    paths = list(dict.fromkeys(e["path"] for c in claims for e in c["evidence"]))[:MAX_REVERIFY_FILES]
    files: dict[str, dict] = {}
    for path in paths:
        try:
            r = httpx.get(_raw_url(repo["owner"], repo["name"], row["commit_sha"], path),
                          timeout=8, headers={"User-Agent": "socialpilot-verify"})
        except (httpx.HTTPError, PublicationError):
            files[path] = {"status": "unreachable"}
            continue
        if r.status_code != 200:
            files[path] = {"status": "missing" if r.status_code == 404 else "unreachable"}
            continue
        files[path] = {
            "status": "fetched",
            "text": _norm(r.text),
            "matches_ingested_copy": hashlib.sha256(r.text.encode("utf-8")).hexdigest()
            == manifest.get(path, {}).get("sha256"),
        }
    results, confirmed = [], 0
    for index, claim in enumerate(claims):
        if claim["status"] != "supported" or not claim["evidence"]:
            results.append({"index": index, "status": "no_evidence"})
            continue
        ok = all(
            files.get(e["path"], {}).get("status") == "fetched"
            and _norm(e["excerpt"]) in files[e["path"]]["text"]
            for e in claim["evidence"]
        )
        reachable = all(files.get(e["path"], {}).get("status") == "fetched" for e in claim["evidence"])
        status = "confirmed" if ok else ("mismatch" if reachable else "unreachable")
        confirmed += status == "confirmed"
        results.append({"index": index, "status": status})
    return {
        "checked_at": storage._now(),
        "commit_sha": row["commit_sha"],
        "confirmed": confirmed,
        "checked": sum(1 for r in results if r["status"] != "no_evidence"),
        "claims": results,
        "files": {p: {k: v for k, v in f.items() if k != "text"} for p, f in files.items()},
    }


# ----------------------------------------------------------------- ownership proof

def _gh_repo(project: dict) -> tuple[str, str]:
    if not project.get("repository_url"):
        raise PublicationError("Ownership proof needs a project imported from a GitHub repository.")
    try:
        return parse_github_url(project["repository_url"])
    except IngestionError as exc:
        raise PublicationError(str(exc)) from exc


def ownership_status(project_id: str) -> dict:
    with storage.conn() as c:
        row = c.execute("SELECT * FROM project_ownership WHERE project_id=?", (project_id,)).fetchone()
    return {
        "started": row is not None,
        "verified": bool(row and row["verified_at"]),
        "verified_at": row["verified_at"] if row else None,
        "token": row["token"] if row and not row["verified_at"] else None,
    }


def start_ownership(user_id: str, project_id: str) -> dict:
    project, _docs, _r = _owned_project(user_id, project_id)
    owner, repo = _gh_repo(project)
    with storage.conn() as c:
        row = c.execute("SELECT token FROM project_ownership WHERE project_id=?", (project_id,)).fetchone()
        token = row["token"] if row else f"socialpilot-verify-{secrets.token_hex(16)}"
        if row is None:
            c.execute(
                "INSERT INTO project_ownership(project_id,user_id,token,created_at) VALUES(?,?,?,?)",
                (project_id, user_id, token, storage._now()),
            )
    return {
        "token": token, "file": OWNERSHIP_FILE, "repository": f"https://github.com/{owner}/{repo}",
        "instructions": (
            f"Add a file named {OWNERSHIP_FILE} to the root of the default branch of "
            f"{owner}/{repo} containing exactly the token above, commit it, then check again. "
            "You can delete the file afterwards; the proof is recorded when it is checked."
        ),
    }


def check_ownership(user_id: str, project_id: str) -> dict:
    project, _docs, _r = _owned_project(user_id, project_id)
    owner, repo = _gh_repo(project)
    with storage.conn() as c:
        row = c.execute("SELECT token,verified_at FROM project_ownership WHERE project_id=?", (project_id,)).fetchone()
    if row is None:
        raise PublicationError("Start the ownership check first.")
    if row["verified_at"]:
        return ownership_status(project_id)
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{OWNERSHIP_FILE}"
    try:
        r = httpx.get(url, timeout=8, headers={"User-Agent": "socialpilot-verify"})
    except httpx.HTTPError as exc:
        raise PublicationError("Could not reach GitHub. Try again in a moment.") from exc
    if r.status_code != 200 or row["token"] not in r.text:
        raise PublicationError(
            f"{OWNERSHIP_FILE} was not found on the default branch with your token yet."
        )
    with storage.conn() as c:
        c.execute("UPDATE project_ownership SET verified_at=? WHERE project_id=?",
                  (storage._now(), project_id))
    return ownership_status(project_id)


# ------------------------------------------------------------- sharing to the feed

_SECTION_TITLES = {
    "summary": None, "problem": "Problem", "architecture": "Architecture",
    "implementation": "Implementation", "challenges": "Challenges", "results": "Results",
    "limitations": "Limitations", "future_work": "What's next",
}


def _clip(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("\n"))
    return (cut[: end + 1] if end > limit // 2 else cut.rstrip() + "…").strip()


def case_study_post_body(content: dict, note: str = "", max_chars: int = 7000) -> str:
    """Feed-sized Markdown teaser of a case study. The full text + evidence live on its
    public page; this is only built from the same frozen content."""
    parts = []
    if note.strip():
        parts.append(note.strip())
    parts.append(f"## {content.get('title') or 'Case study'}")
    if content.get("summary"):
        parts.append(_clip(content["summary"], 900))
    for section in CASE_SECTIONS[1:]:
        text = (content.get(section) or "").strip()
        if text:
            parts.append(f"**{_SECTION_TITLES[section]}.** {_clip(text, 450)}")
    body = "\n\n".join(parts)
    return _clip(body, max_chars)
