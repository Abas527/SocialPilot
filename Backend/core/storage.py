import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from config import settings
from core import migrations
from core.rag.chunking import chunk_documents
from core.schemas import Chunk, SourceDocument
import re


_migrated: set[str] = set()   # run migrations once per process per database


def _prep(sql, params):
    if params is None:
        return sql, ()
    if isinstance(params, dict):
        # convert :name placeholders to positional ?, in order of appearance
        names = re.findall(r":([A-Za-z_]\w*)", sql)
        return re.sub(r":[A-Za-z_]\w*", "?", sql), tuple(params[n] for n in names)
    if isinstance(params, (list, tuple)):
        return sql, tuple(params)
    return sql, tuple(params)   # sets, generators, etc.

class _Row:
    """sqlite3.Row-like: access by index or column name."""
    __slots__ = ("_cols", "_vals")
    def __init__(self, cols, vals):
        self._cols, self._vals = cols, tuple(vals)
    def __getitem__(self, k):
        if isinstance(k, str):
            return self._vals[self._cols.index(k)]
        return self._vals[k]
    def keys(self):
        return list(self._cols)
    def __iter__(self):
        return iter(self._vals)
    def __len__(self):
        return len(self._vals)

class _Cursor:
    def __init__(self, cur):
        self._cur = cur
    def _cols(self):
        return [d[0] for d in (self._cur.description or [])]
    def _wrap(self, r):
        return None if r is None else _Row(self._cols(), r)
    def fetchone(self):
        return self._wrap(self._cur.fetchone())
    def fetchall(self):
        cols = self._cols()
        return [_Row(cols, r) for r in self._cur.fetchall()]
    def __iter__(self):
        return iter(self.fetchall())
    @property
    def lastrowid(self):
        return self._cur.lastrowid
    @property
    def rowcount(self):
        return self._cur.rowcount

class _LibsqlConn:
    def __init__(self, raw):
        self._raw = raw
    def execute(self, sql, params=()):
        sql, params = _prep(sql, params)
        return _Cursor(self._raw.execute(sql, params))
    def executemany(self, sql, seq):
        return _Cursor(self._raw.executemany(sql, seq))
    def executescript(self, script):
        return self._raw.executescript(script)
    def commit(self):
        self._raw.commit()
    def rollback(self):
        self._raw.rollback()
    def close(self):
        self._raw.close()

def _open(path: str):
    url = settings.db_url 
    if url:
        import libsql  # pip install libsql
        c = libsql.connect(database=url, auth_token=settings.db_auth_token)
        return _LibsqlConn(c), url
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c, path

@contextmanager
def conn(db_path: str | None = None):
    path = db_path or settings.db_path
    c, key = _open(path)
    try:
        if key not in _migrated:
            migrations.migrate(c)
            _migrated.add(key)
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_project(name: str, repository_url: str | None, commit_sha: str | None,
                   docs: list[dict], db_path: str | None = None,
                   owner_user_id: str | None = None) -> str:
    pid = uuid.uuid4().hex
    source_docs = [SourceDocument(**doc) for doc in docs]
    chunks = chunk_documents(source_docs, settings.chunk_chars)
    with conn(db_path) as c:
        c.execute("INSERT INTO projects VALUES(?,?,?,?,?,?)", (pid, name, repository_url, commit_sha, None, _now()))
        if owner_user_id:
            c.execute(
                "INSERT INTO project_owners(project_id,user_id,assigned_at) VALUES(?,?,?)",
                (pid, owner_user_id, _now()),
            )
        c.executemany(
            "INSERT INTO source_documents VALUES(?,?,?,?,?,?)",
            [(pid, d["source_id"], d["path"], d["content"], d.get("source_url"), d.get("commit_sha")) for d in docs],
        )
        _save_chunks(c, pid, chunks)
    return pid


def _save_chunks(c: sqlite3.Connection, project_id: str, chunks: list[Chunk]) -> None:
    c.execute("DELETE FROM project_chunks WHERE project_id=?", (project_id,))
    c.executemany(
        """INSERT INTO project_chunks
        (project_id,chunk_id,source_id,path,text,start_line,end_line,heading,source_url)
        VALUES(?,?,?,?,?,?,?,?,?)""",
        [
            (
                project_id, chunk.chunk_id, chunk.source_id, chunk.path, chunk.text,
                chunk.start_line, chunk.end_line, chunk.heading, chunk.source_url,
            )
            for chunk in chunks
        ],
    )
    c.execute(
        """INSERT INTO project_rag_index(project_id,chunk_chars,chunk_count,indexed_at)
        VALUES(?,?,?,?)
        ON CONFLICT(project_id) DO UPDATE SET
        chunk_chars=excluded.chunk_chars, chunk_count=excluded.chunk_count,
        indexed_at=excluded.indexed_at""",
        (project_id, settings.chunk_chars, len(chunks), _now()),
    )


def rebuild_project_index(project_id: str, db_path: str | None = None) -> dict | None:
    with conn(db_path) as c:
        exists = c.execute(
            "SELECT 1 FROM projects WHERE project_id=?", (project_id,)
        ).fetchone()
        if not exists:
            return None
        rows = c.execute(
            """SELECT source_id,path,content,source_url,commit_sha
            FROM source_documents WHERE project_id=? ORDER BY path""",
            (project_id,),
        ).fetchall()
        docs = [SourceDocument(**dict(row)) for row in rows]
        chunks = chunk_documents(docs, settings.chunk_chars)
        _save_chunks(c, project_id, chunks)
        row = c.execute(
            """SELECT project_id,chunk_chars,chunk_count,indexed_at
            FROM project_rag_index WHERE project_id=?""",
            (project_id,),
        ).fetchone()
        return dict(row)


def get_project_chunks(project_id: str, db_path: str | None = None) -> list[Chunk] | None:
    with conn(db_path) as c:
        exists = c.execute(
            "SELECT 1 FROM projects WHERE project_id=?", (project_id,)
        ).fetchone()
        if not exists:
            return None
        rows = c.execute(
            """SELECT chunk_id,source_id,path,text,start_line,end_line,heading,source_url
            FROM project_chunks WHERE project_id=? ORDER BY path,start_line,chunk_id""",
            (project_id,),
        ).fetchall()
    return [Chunk(**dict(row)) for row in rows]


def count_project_chunks(
    project_id: str,
    path: str | None = None,
    db_path: str | None = None,
) -> int | None:
    with conn(db_path) as c:
        exists = c.execute(
            "SELECT 1 FROM projects WHERE project_id=?", (project_id,)
        ).fetchone()
        if not exists:
            return None
        if path:
            row = c.execute(
                "SELECT COUNT(*) AS total FROM project_chunks WHERE project_id=? AND path=?",
                (project_id, path),
            ).fetchone()
        else:
            row = c.execute(
                "SELECT COUNT(*) AS total FROM project_chunks WHERE project_id=?",
                (project_id,),
            ).fetchone()
    return row["total"]


def get_project_index(project_id: str, db_path: str | None = None) -> dict | None:
    with conn(db_path) as c:
        exists = c.execute(
            "SELECT 1 FROM projects WHERE project_id=?", (project_id,)
        ).fetchone()
        if not exists:
            return None
        row = c.execute(
            """SELECT project_id,chunk_chars,chunk_count,indexed_at
            FROM project_rag_index WHERE project_id=?""",
            (project_id,),
        ).fetchone()
        if row:
            return dict(row)
        count = c.execute(
            "SELECT COUNT(*) AS chunk_count FROM project_chunks WHERE project_id=?",
            (project_id,),
        ).fetchone()["chunk_count"]
        return {
            "project_id": project_id,
            "chunk_chars": settings.chunk_chars,
            "chunk_count": count,
            "indexed_at": None,
        }


def ensure_project_index(project_id: str, db_path: str | None = None) -> dict | None:
    index = get_project_index(project_id, db_path)
    if index is None:
        return None
    with conn(db_path) as c:
        source_count = c.execute(
            "SELECT COUNT(*) AS source_count FROM source_documents WHERE project_id=?",
            (project_id,),
        ).fetchone()["source_count"]
    if (
        index["indexed_at"] is None
        or index["chunk_chars"] != settings.chunk_chars
        or (source_count > 0 and index["chunk_count"] == 0)
    ):
        return rebuild_project_index(project_id, db_path)
    return index


def save_profile(project_id: str, profile: dict, db_path: str | None = None) -> None:
    with conn(db_path) as c:
        c.execute("UPDATE projects SET profile_json=?, name=? WHERE project_id=?",
                  (json.dumps(profile), profile.get("name"), project_id))


def get_project(project_id: str, db_path: str | None = None) -> dict | None:
    with conn(db_path) as c:
        p = c.execute("SELECT * FROM projects WHERE project_id=?", (project_id,)).fetchone()
        if not p:
            return None
        docs = c.execute("SELECT source_id,path,content,source_url,commit_sha FROM source_documents WHERE project_id=?",
                         (project_id,)).fetchall()
        arts = c.execute("SELECT * FROM artifacts WHERE project_id=?", (project_id,)).fetchall()
    out = dict(p)
    out["profile"] = json.loads(p["profile_json"]) if p["profile_json"] else None
    out["documents"] = [dict(d) for d in docs]
    out["artifacts"] = {a["artifact_type"]: {
        "generated": json.loads(a["generated_json"]),
        "edited": json.loads(a["edited_json"]) if a["edited_json"] else None,
        "updated_at": a["updated_at"]} for a in arts}
    return out


def list_projects(
    db_path: str | None = None,
    limit: int = 50,
    offset: int = 0,
    query: str | None = None,
    owner_user_id: str | None = None,
) -> list[dict]:
    if not 1 <= limit <= 100 or offset < 0:
        raise ValueError("Project pagination requires limit 1-100 and offset >= 0.")
    sql = """SELECT p.project_id,p.name,p.repository_url,p.created_at
    FROM projects p"""
    params: list[str | int] = []
    filters = []
    if owner_user_id:
        sql += " JOIN project_owners po ON po.project_id=p.project_id"
        filters.append("po.user_id=?")
        params.append(owner_user_id)
    if query and query.strip():
        filters.append("(p.name LIKE ? OR p.repository_url LIKE ?)")
        pattern = f"%{query.strip()}%"
        params.extend((pattern, pattern))
    if filters:
        sql += " WHERE " + " AND ".join(filters)
    sql += " ORDER BY p.created_at DESC LIMIT ? OFFSET ?"
    params.extend((limit, offset))
    with conn(db_path) as c:
        return [dict(row) for row in c.execute(sql, params)]


def list_project_documents(project_id: str, db_path: str | None = None) -> list[dict] | None:
    with conn(db_path) as c:
        exists = c.execute(
            "SELECT 1 FROM projects WHERE project_id=?", (project_id,)
        ).fetchone()
        if not exists:
            return None
        rows = c.execute(
            """SELECT source_id,path,source_url,commit_sha,length(content) AS size_chars
            FROM source_documents WHERE project_id=? ORDER BY path""",
            (project_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_project_chunks_page(
    project_id: str,
    limit: int = 50,
    offset: int = 0,
    path: str | None = None,
    db_path: str | None = None,
) -> tuple[int, list[Chunk]] | None:
    if not 1 <= limit <= 100 or offset < 0:
        raise ValueError("Chunk pagination requires limit 1-100 and offset >= 0.")
    with conn(db_path) as c:
        exists = c.execute(
            "SELECT 1 FROM projects WHERE project_id=?", (project_id,)
        ).fetchone()
        if not exists:
            return None
        if path:
            total = c.execute(
                "SELECT COUNT(*) AS total FROM project_chunks WHERE project_id=? AND path=?",
                (project_id, path),
            ).fetchone()["total"]
        else:
            total = c.execute(
                "SELECT COUNT(*) AS total FROM project_chunks WHERE project_id=?",
                (project_id,),
            ).fetchone()["total"]
        sql = """SELECT chunk_id,source_id,path,text,start_line,end_line,heading,source_url
        FROM project_chunks WHERE project_id=?"""
        params: list[str | int] = [project_id]
        if path:
            sql += " AND path=?"
            params.append(path)
        sql += " ORDER BY path,start_line,chunk_id LIMIT ? OFFSET ?"
        params.extend((limit, offset))
        rows = c.execute(sql, params).fetchall()
    return total, [Chunk(**dict(row)) for row in rows]


def get_project_artifact(
    project_id: str,
    artifact_type: str,
    db_path: str | None = None,
) -> dict | None:
    with conn(db_path) as c:
        row = c.execute(
            """SELECT generated_json,edited_json,created_at,updated_at FROM artifacts
            WHERE project_id=? AND artifact_type=?""",
            (project_id, artifact_type),
        ).fetchone()
    if not row:
        return None
    return {
        "artifact_type": artifact_type,
        "generated": json.loads(row["generated_json"]),
        "edited": json.loads(row["edited_json"]) if row["edited_json"] else None,
        "current": json.loads(row["edited_json"] or row["generated_json"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get_project_workflow_state(project_id: str, db_path: str | None = None) -> dict | None:
    with conn(db_path) as c:
        project = c.execute(
            """SELECT project_id,name,repository_url,profile_json,created_at
            FROM projects WHERE project_id=?""",
            (project_id,),
        ).fetchone()
        if not project:
            return None
        source_count = c.execute(
            "SELECT COUNT(*) AS source_count FROM source_documents WHERE project_id=?",
            (project_id,),
        ).fetchone()["source_count"]
        artifacts = c.execute(
            """SELECT artifact_type,edited_json IS NOT NULL AS has_edits,
            created_at,updated_at FROM artifacts WHERE project_id=?
            ORDER BY artifact_type""",
            (project_id,),
        ).fetchall()
    profile = json.loads(project["profile_json"]) if project["profile_json"] else None
    findings = profile.get("findings", []) if profile else []
    supported_count = sum(
        1 for finding in findings if finding.get("status") == "supported"
    )
    return {
        "project_id": project["project_id"],
        "name": project["name"],
        "repository_url": project["repository_url"],
        "created_at": project["created_at"],
        "source_count": source_count,
        "analysis_available": profile is not None,
        "finding_count": len(findings),
        "supported_finding_count": supported_count,
        "artifacts": [
            {
                "artifact_type": row["artifact_type"],
                "has_edits": bool(row["has_edits"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in artifacts
        ],
    }


def delete_project(project_id: str, db_path: str | None = None) -> bool:
    with conn(db_path) as c:
        exists = c.execute(
            "SELECT 1 FROM projects WHERE project_id=?", (project_id,)
        ).fetchone()
        if not exists:
            return False
        c.execute("DELETE FROM artifacts WHERE project_id=?", (project_id,))
        c.execute("DELETE FROM source_documents WHERE project_id=?", (project_id,))
        c.execute("DELETE FROM project_chunks WHERE project_id=?", (project_id,))
        c.execute("DELETE FROM project_rag_index WHERE project_id=?", (project_id,))
        c.execute("DELETE FROM projects WHERE project_id=?", (project_id,))
    return True


def save_artifact(project_id: str, artifact_type: str, content: dict, edited: bool = False,
                  db_path: str | None = None) -> None:
    """Generated and edited versions are kept separately so users can revert."""
    now, blob = _now(), json.dumps(content)
    with conn(db_path) as c:
        if not c.execute(
            "SELECT 1 FROM projects WHERE project_id=?", (project_id,)
        ).fetchone():
            raise KeyError("Project not found")
        row = c.execute("SELECT artifact_id FROM artifacts WHERE project_id=? AND artifact_type=?",
                        (project_id, artifact_type)).fetchone()
        if row and edited:
            c.execute("UPDATE artifacts SET edited_json=?, updated_at=? WHERE artifact_id=?", (blob, now, row["artifact_id"]))
        elif row:
            c.execute("UPDATE artifacts SET generated_json=?, edited_json=NULL, updated_at=? WHERE artifact_id=?",
                      (blob, now, row["artifact_id"]))
        elif edited:
            raise KeyError("Artifact not found; generate it before saving edits.")
        else:
            c.execute("INSERT INTO artifacts VALUES(?,?,?,?,?,?,?)",
                      (uuid.uuid4().hex, project_id, artifact_type, blob, blob if edited else None, now, now))


def revert_artifact(project_id: str, artifact_type: str, db_path: str | None = None) -> bool:
    with conn(db_path) as c:
        row = c.execute(
            "SELECT artifact_id FROM artifacts WHERE project_id=? AND artifact_type=?",
            (project_id, artifact_type),
        ).fetchone()
        if not row:
            if not c.execute(
                "SELECT 1 FROM projects WHERE project_id=?", (project_id,)
            ).fetchone():
                raise KeyError("Project not found")
            return False
        c.execute(
            "UPDATE artifacts SET edited_json=NULL, updated_at=? WHERE artifact_id=?",
            (_now(), row["artifact_id"]),
        )
    return True


def create_user(
    email: str,
    display_name: str,
    password_hash: str | None = None,
    db_path: str | None = None,
) -> str:
    normalized_email = email.strip().lower()
    normalized_name = display_name.strip()
    if not normalized_email or not normalized_name:
        raise ValueError("Email and display name must not be empty.")
    if password_hash is not None and not password_hash:
        raise ValueError("Password hashes must not be empty.")
    now = _now()
    user_id = uuid.uuid4().hex
    username = f"user_{user_id[:12]}"
    with conn(db_path) as c:
        try:
            c.execute(
                """INSERT INTO users
                (user_id,email,display_name,password_hash,created_at,updated_at,username)
                VALUES(?,?,?,?,?,?,?)""",
                (
                    user_id,
                    normalized_email,
                    normalized_name,
                    password_hash,
                    now,
                    now,
                    username,
                ),
            )
        except sqlite3.IntegrityError as exc:
            if c.execute("SELECT 1 FROM users WHERE email=?", (normalized_email,)).fetchone():
                raise ValueError("A user with this email already exists.") from exc
            raise
    return user_id


def get_user(user_id: str, db_path: str | None = None) -> dict | None:
    with conn(db_path) as c:
        row = c.execute(
            """SELECT user_id,email,display_name,created_at,updated_at
            FROM users WHERE user_id=?""",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def get_user_by_email(email: str, db_path: str | None = None) -> dict | None:
    with conn(db_path) as c:
        row = c.execute(
            """SELECT user_id,email,display_name,password_hash,verified_at,is_demo,
            created_at,updated_at
            FROM users WHERE email=?""",
            (email.strip(),),
        ).fetchone()
    return dict(row) if row else None


def create_email_verification_token(
    user_id: str,
    raw_token: str,
    expires_at: str,
    db_path: str | None = None,
) -> str:
    token_hash = _token_digest(raw_token)
    created_at = _now()
    normalized_expiry = _normalized_expiry(expires_at)
    token_id = uuid.uuid4().hex
    with conn(db_path) as c:
        user = c.execute(
            "SELECT verified_at FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
        if user is None:
            raise KeyError("User not found.")
        if user["verified_at"] is not None:
            raise ValueError("User email is already verified.")
        c.execute(
            """UPDATE email_verification_tokens SET used_at=?
            WHERE user_id=? AND used_at IS NULL""",
            (created_at, user_id),
        )
        c.execute(
            """INSERT INTO email_verification_tokens
            (token_id,user_id,token_hash,created_at,expires_at,used_at)
            VALUES(?,?,?,?,?,NULL)""",
            (token_id, user_id, token_hash, created_at, normalized_expiry),
        )
    return token_id


def verify_email_token(raw_token: str, db_path: str | None = None) -> bool:
    token_hash = _token_digest(raw_token)
    now = _now()
    with conn(db_path) as c:
        c.execute("BEGIN IMMEDIATE")
        token = c.execute(
            """SELECT token_id,user_id FROM email_verification_tokens
            WHERE token_hash=? AND used_at IS NULL AND expires_at>?""",
            (token_hash, now),
        ).fetchone()
        if token is None:
            return False
        c.execute(
            "UPDATE email_verification_tokens SET used_at=? WHERE token_id=?",
            (now, token["token_id"]),
        )
        c.execute(
            """UPDATE users SET verified_at=?,updated_at=?
            WHERE user_id=? AND verified_at IS NULL""",
            (now, now, token["user_id"]),
        )
        return c.execute(
            "SELECT changes() AS changed"
        ).fetchone()["changed"] == 1


def _token_digest(raw_token: str) -> str:
    if not raw_token:
        raise ValueError("Session token must not be empty.")
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _normalized_expiry(expires_at: str) -> str:
    try:
        expiry = datetime.fromisoformat(expires_at)
    except (TypeError, ValueError) as exc:
        raise ValueError("Session expiry must be an ISO 8601 datetime.") from exc
    if expiry.tzinfo is None:
        raise ValueError("Session expiry must include a timezone.")
    expiry = expiry.astimezone(timezone.utc)
    if expiry <= datetime.now(timezone.utc):
        raise ValueError("Session expiry must be in the future.")
    return expiry.isoformat()


def create_auth_session(
    user_id: str,
    raw_token: str,
    expires_at: str,
    db_path: str | None = None,
) -> str:
    token_hash = _token_digest(raw_token)
    created_at = _now()
    normalized_expiry = _normalized_expiry(expires_at)
    session_id = uuid.uuid4().hex
    with conn(db_path) as c:
        if not c.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,)).fetchone():
            raise KeyError("User not found.")
        c.execute(
            """INSERT INTO auth_sessions
            (session_id,user_id,token_hash,created_at,expires_at,revoked_at)
            VALUES(?,?,?,?,?,NULL)""",
            (session_id, user_id, token_hash, created_at, normalized_expiry),
        )
    return session_id


def revoke_auth_session_by_id(
    session_id: str,
    user_id: str,
    db_path: str | None = None,
) -> bool:
    with conn(db_path) as c:
        cursor = c.execute(
            """UPDATE auth_sessions SET revoked_at=?
            WHERE session_id=? AND user_id=? AND revoked_at IS NULL""",
            (_now(), session_id, user_id),
        )
    return cursor.rowcount > 0


def get_active_auth_session(
    raw_token: str,
    db_path: str | None = None,
) -> dict | None:
    token_hash = _token_digest(raw_token)
    with conn(db_path) as c:
        row = c.execute(
            """SELECT s.session_id,s.user_id,s.created_at,s.expires_at,
            u.email,u.display_name
            FROM auth_sessions s JOIN users u ON u.user_id=s.user_id
            WHERE s.token_hash=? AND s.revoked_at IS NULL AND s.expires_at>?
            AND u.verified_at IS NOT NULL""",
            (token_hash, _now()),
        ).fetchone()
    return dict(row) if row else None


def revoke_auth_session(raw_token: str, db_path: str | None = None) -> bool:
    token_hash = _token_digest(raw_token)
    with conn(db_path) as c:
        cursor = c.execute(
            """UPDATE auth_sessions SET revoked_at=?
            WHERE token_hash=? AND revoked_at IS NULL""",
            (_now(), token_hash),
        )
    return cursor.rowcount > 0


def assign_project_owner(
    project_id: str,
    user_id: str,
    db_path: str | None = None,
) -> None:
    now = _now()
    with conn(db_path) as c:
        if not c.execute(
            "SELECT 1 FROM projects WHERE project_id=?", (project_id,)
        ).fetchone():
            raise KeyError("Project not found.")
        if not c.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,)).fetchone():
            raise KeyError("User not found.")
        c.execute(
            """INSERT INTO project_owners(project_id,user_id,assigned_at)
            VALUES(?,?,?)
            ON CONFLICT(project_id) DO UPDATE SET
            user_id=excluded.user_id,assigned_at=excluded.assigned_at""",
            (project_id, user_id, now),
        )


def get_project_owner(
    project_id: str,
    db_path: str | None = None,
) -> dict | None:
    with conn(db_path) as c:
        row = c.execute(
            """SELECT po.project_id,po.user_id,po.assigned_at,u.email,u.display_name
            FROM project_owners po JOIN users u ON u.user_id=po.user_id
            WHERE po.project_id=?""",
            (project_id,),
        ).fetchone()
    return dict(row) if row else None


def database_status(db_path: str | None = None) -> dict:
    with conn(db_path) as c:
        version = c.execute(
            "SELECT COALESCE(MAX(version),0) AS version,COUNT(*) AS count FROM schema_migrations"
        ).fetchone()
        sqlite_version = c.execute("SELECT sqlite_version() AS version").fetchone()["version"]
    return {
        "engine": "sqlite",
        "ready": True,
        "schema_version": version["version"],
        "migration_count": version["count"],
        "sqlite_version": sqlite_version,
    }
