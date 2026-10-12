"""Persisted public profiles, follows, and explicitly shared feed posts."""
import json
import logging
import re
import sqlite3
import uuid
from urllib.parse import urlsplit

from core import notifications, storage

_USERNAME_PATTERN = re.compile(r"^[a-z0-9_]{3,30}$")
_TAG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9+#._-]{0,29}$")
_TIMEZONE_PATTERN = re.compile(
    r"^(?:[A-Za-z_]+(?:/[A-Za-z_+\-0-9]+){0,2}|UTC(?:[+-]\d{1,2}(?::\d{2})?)?)$"
)
AVAILABILITY = ("none", "open_to_work", "hiring", "open_to_collab")
MAX_TAGS = 5
MAX_SKILLS = 15
MAX_POST_CHARS = 8000
MAX_COMMENT_CHARS = 1000


class SocialError(ValueError):
    pass


def normalize_tags(values: list[str], limit: int, label: str = "tags") -> list[str]:
    """Lowercase, strip a leading '#', de-duplicate (order kept) and validate."""
    seen: list[str] = []
    for value in values:
        tag = value.strip().lstrip("#").lower()
        if not _TAG_PATTERN.fullmatch(tag):
            raise SocialError(
                f"Invalid entry in {label}: use 1-30 letters, digits, or + # . _ -."
            )
        if tag not in seen:
            seen.append(tag)
    if len(seen) > limit:
        raise SocialError(f"At most {limit} {label} are allowed.")
    return seen


def _finish_profile(profile: dict) -> dict:
    profile["is_following"] = bool(profile["is_following"])
    profile["is_demo"] = bool(profile["is_demo"])
    profile["skills"] = json.loads(profile.get("skills") or "[]")
    return profile


def update_profile(
    user_id: str,
    username: str | None = None,
    display_name: str | None = None,
    bio: str | None = None,
    skills: list[str] | None = None,
    timezone: str | None = None,
    availability: str | None = None,
) -> dict:
    updates = {}
    if username is not None:
        username = username.strip().lower()
        if not _USERNAME_PATTERN.fullmatch(username):
            raise SocialError("Username must be 3-30 lowercase letters, digits, or underscores.")
        updates["username"] = username
    if display_name is not None:
        display_name = display_name.strip()
        if not display_name:
            raise SocialError("Display name must not be blank.")
        updates["display_name"] = display_name
    if bio is not None:
        updates["bio"] = bio.strip()
    if skills is not None:
        updates["skills"] = json.dumps(normalize_tags(skills, MAX_SKILLS, "skills"))
    if timezone is not None:
        timezone = timezone.strip()
        if timezone and not _TIMEZONE_PATTERN.fullmatch(timezone):
            raise SocialError("Timezone must look like Asia/Kathmandu or UTC+5:45.")
        updates["timezone"] = timezone
    if availability is not None:
        if availability not in AVAILABILITY:
            raise SocialError(f"Availability must be one of {list(AVAILABILITY)}.")
        updates["availability"] = availability

    with storage.conn() as connection:
        if not connection.execute(
            "SELECT 1 FROM users WHERE user_id=?", (user_id,)
        ).fetchone():
            raise KeyError("User not found.")
        if updates:
            updates["updated_at"] = storage._now()
            assignments = ",".join(f"{key}=?" for key in updates)
            try:
                connection.execute(
                    f"UPDATE users SET {assignments} WHERE user_id=?",
                    (*updates.values(), user_id),
                )
            except sqlite3.IntegrityError as exc:
                if "username" in updates and connection.execute(
                    "SELECT 1 FROM users WHERE username=? COLLATE NOCASE AND user_id!=?",
                    (updates["username"], user_id),
                ).fetchone():
                    raise SocialError("That username is already taken.") from exc
                raise
    return get_profile_by_id(user_id)


def get_profile_by_id(user_id: str, viewer_id: str | None = None) -> dict:
    with storage.conn() as connection:
        row = connection.execute(
            """SELECT u.user_id,u.username,u.display_name,u.bio,u.is_demo,
            u.skills,u.timezone,u.availability,
            CASE WHEN u.wallet_verified_at IS NOT NULL THEN u.wallet_address END
                AS wallet_address,
            (SELECT COUNT(*) FROM follows f WHERE f.followed_user_id=u.user_id)
                AS follower_count,
            (SELECT COUNT(*) FROM follows f WHERE f.follower_user_id=u.user_id)
                AS following_count,
            EXISTS(SELECT 1 FROM follows f
                WHERE f.follower_user_id=? AND f.followed_user_id=u.user_id)
                AS is_following
            FROM users u WHERE u.user_id=? AND u.verified_at IS NOT NULL""",
            (viewer_id or "", user_id),
        ).fetchone()
    if row is None:
        raise KeyError("Profile not found.")
    return _finish_profile(dict(row))


def get_profile_by_username(username: str, viewer_id: str) -> dict:
    with storage.conn() as connection:
        row = connection.execute(
            "SELECT user_id FROM users WHERE username=? COLLATE NOCASE AND verified_at IS NOT NULL",
            (username,),
        ).fetchone()
    if row is None:
        raise KeyError("Profile not found.")
    return get_profile_by_id(row["user_id"], viewer_id)


def list_profiles(
    viewer_id: str,
    query: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    if not 1 <= limit <= 50 or offset < 0:
        raise ValueError("Profile pagination requires limit 1-50 and offset >= 0.")
    sql = """SELECT u.user_id,u.username,u.display_name,u.bio,u.is_demo,
            u.skills,u.timezone,u.availability,
        CASE WHEN u.wallet_verified_at IS NOT NULL THEN u.wallet_address END
            AS wallet_address,
        (SELECT COUNT(*) FROM follows f WHERE f.followed_user_id=u.user_id)
            AS follower_count,
        (SELECT COUNT(*) FROM follows f WHERE f.follower_user_id=u.user_id)
            AS following_count,
        EXISTS(SELECT 1 FROM follows f
            WHERE f.follower_user_id=? AND f.followed_user_id=u.user_id)
            AS is_following
        FROM users u WHERE u.verified_at IS NOT NULL AND u.user_id!=?"""
    params: list[str | int] = [viewer_id, viewer_id]
    if query and query.strip():
        sql += " AND (u.username LIKE ? OR u.display_name LIKE ?)"
        term = f"%{query.strip()}%"
        params.extend((term, term))
    sql += " ORDER BY u.username COLLATE NOCASE LIMIT ? OFFSET ?"
    params.extend((limit, offset))
    with storage.conn() as connection:
        profiles = [dict(row) for row in connection.execute(sql, params)]
    return [_finish_profile(profile) for profile in profiles]


def follow(follower_id: str, username: str) -> bool:
    target = get_profile_by_username(username, follower_id)
    if target["user_id"] == follower_id:
        raise SocialError("You cannot follow your own profile.")
    with storage.conn() as connection:
        cursor = connection.execute(
            "INSERT OR IGNORE INTO follows(follower_user_id,followed_user_id,created_at) VALUES(?,?,?)",
            (follower_id, target["user_id"], storage._now()),
        )
        if cursor.rowcount > 0:
            notifications.notify(connection, target["user_id"], follower_id, "follow")
    return cursor.rowcount > 0


def unfollow(follower_id: str, username: str) -> bool:
    target = get_profile_by_username(username, follower_id)
    with storage.conn() as connection:
        cursor = connection.execute(
            "DELETE FROM follows WHERE follower_user_id=? AND followed_user_id=?",
            (follower_id, target["user_id"]),
        )
    return cursor.rowcount > 0


def list_follows(
    username: str, viewer_id: str, direction: str = "followers",
    limit: int = 20, offset: int = 0,
) -> list[dict]:
    """People who follow `username` ('followers') or whom they follow ('following')."""
    if direction not in {"followers", "following"}:
        raise ValueError("direction must be 'followers' or 'following'.")
    if not 1 <= limit <= 50 or offset < 0:
        raise ValueError("Pagination requires limit 1-50 and offset >= 0.")
    target = get_profile_by_username(username, viewer_id)
    near, far = (
        ("followed_user_id", "follower_user_id")
        if direction == "followers"
        else ("follower_user_id", "followed_user_id")
    )
    with storage.conn() as connection:
        ids = [
            row[0]
            for row in connection.execute(
                f"""SELECT f.{far} FROM follows f JOIN users u ON u.user_id=f.{far}
                WHERE f.{near}=? AND u.verified_at IS NOT NULL
                ORDER BY f.created_at DESC LIMIT ? OFFSET ?""",
                (target["user_id"], limit, offset),
            )
        ]
    return [get_profile_by_id(user_id, viewer_id) for user_id in ids]


# --------------------------------------------------------------------------- posts

_ARTIFACT_REF = re.compile(
    r"^(case_study|community_post|linkedin:(technical_lesson|engineering_decision|personal_reflection))$"
)


def _validate_link(url: str | None) -> str | None:
    if url is None or not url.strip():
        return None
    url = url.strip()
    parts = urlsplit(url)
    if len(url) > 2048 or parts.scheme not in {"http", "https"} or not parts.netloc:
        raise SocialError("Link must be a valid http(s) URL.")
    return url


def _validate_body(body: str) -> str:
    normalized = body.strip()
    if not normalized or len(normalized) > MAX_POST_CHARS:
        raise SocialError(f"Post text must contain 1-{MAX_POST_CHARS} characters.")
    return normalized


def _evidence_snapshot(connection, user_id: str, project_id: str, artifact_ref: str):
    """Count supported claims in the author's own artifact at publish time."""
    owner = connection.execute(
        "SELECT 1 FROM project_owners WHERE project_id=? AND user_id=?",
        (project_id, user_id),
    ).fetchone()
    if owner is None:
        raise KeyError("Project not found.")
    row = connection.execute(
        """SELECT generated_json,edited_json FROM artifacts
        WHERE project_id=? AND artifact_type=?""",
        (project_id, artifact_ref),
    ).fetchone()
    if row is None:
        raise SocialError("That project has no generated content for the chosen artifact.")
    content = json.loads(row["edited_json"] or row["generated_json"])
    claims = content.get("verified_claims") or []
    supported = sum(1 for claim in claims if claim.get("status") == "supported")
    return supported, len(claims)


def create_post(
    user_id: str,
    body: str,
    format: str = "plain",
    tags: list[str] | None = None,
    project_id: str | None = None,
    artifact_ref: str | None = None,
    link_url: str | None = None,
    publication_id: str | None = None,
    attach_evidence: bool = True,
) -> dict:
    """Publish a post. With a project, the text is frozen into an evidence passport
    (a `publication`) that any reader can inspect; see core/publications.py."""
    normalized = _validate_body(body)
    if format not in {"plain", "markdown"}:
        raise SocialError("Format must be 'plain' or 'markdown'.")
    clean_tags = normalize_tags(tags or [], MAX_TAGS)
    link = _validate_link(link_url)
    if artifact_ref is not None and not _ARTIFACT_REF.fullmatch(artifact_ref):
        raise SocialError("artifact_ref must be 'case_study' or 'linkedin:<angle>'.")
    if artifact_ref and not project_id:
        raise SocialError("artifact_ref requires project_id.")
    post_id = uuid.uuid4().hex
    created_at = storage._now()
    with storage.conn() as connection:
        user = connection.execute(
            "SELECT 1 FROM users WHERE user_id=? AND verified_at IS NOT NULL",
            (user_id,),
        ).fetchone()
        if user is None:
            raise KeyError("Verified user not found.")
        if publication_id and not connection.execute(
            """SELECT 1 FROM publications WHERE publication_id=? AND user_id=?
            AND revoked_at IS NULL""",
            (publication_id, user_id),
        ).fetchone():
            raise KeyError("Publication not found.")
        supported = total = None
        if project_id:
            if artifact_ref:
                supported, total = _evidence_snapshot(
                    connection, user_id, project_id, artifact_ref
                )
            elif not connection.execute(
                "SELECT 1 FROM project_owners WHERE project_id=? AND user_id=?",
                (project_id, user_id),
            ).fetchone():
                raise KeyError("Project not found.")
        if project_id and not publication_id and attach_evidence:
            publication_id = _try_publish_evidence(user_id, project_id, normalized, artifact_ref)
        connection.execute(
            """INSERT INTO social_posts
            (post_id,user_id,body,created_at,format,link_url,project_id,artifact_ref,
            evidence_supported,evidence_total,publication_id)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (post_id, user_id, normalized, created_at, format, link, project_id,
             artifact_ref, supported, total, publication_id),
        )
        connection.executemany(
            "INSERT INTO post_tags(post_id,tag) VALUES(?,?)",
            [(post_id, tag) for tag in clean_tags],
        )
    return get_post(post_id, user_id)


def _try_publish_evidence(user_id: str, project_id: str, body: str, artifact_ref: str | None):
    """Create the evidence passport for a post. A failure must not block posting."""
    from core import publications  # lazy: pulls in the AI pipeline

    try:
        return publications.publish_post_text(user_id, project_id, body, artifact_ref)["publication_id"]
    except Exception:  # noqa: BLE001 - evidence is best-effort for plain posts
        logging.getLogger(__name__).warning("Could not build evidence passport", exc_info=True)
        return None


def update_post(
    user_id: str, post_id: str, body: str | None = None, tags: list[str] | None = None,
) -> dict:
    """Edit your own post's text and/or tags (format, project and evidence are fixed)."""
    new_body = _validate_body(body) if body is not None else None
    clean_tags = normalize_tags(tags, MAX_TAGS) if tags is not None else None
    with storage.conn() as connection:
        owned = connection.execute(
            "SELECT publication_id FROM social_posts WHERE post_id=? AND user_id=?",
            (post_id, user_id),
        ).fetchone()
        if owned is None:
            raise KeyError("Post not found.")
        if new_body is not None and owned["publication_id"]:
            raise SocialError(
                "This post carries an evidence passport, so its text is frozen. "
                "Delete it and publish again to change the text."
            )
        if new_body is not None:
            connection.execute(
                "UPDATE social_posts SET body=?,updated_at=? WHERE post_id=?",
                (new_body, storage._now(), post_id),
            )
        if clean_tags is not None:
            connection.execute("DELETE FROM post_tags WHERE post_id=?", (post_id,))
            connection.executemany(
                "INSERT INTO post_tags(post_id,tag) VALUES(?,?)",
                [(post_id, tag) for tag in clean_tags],
            )
            connection.execute(
                "UPDATE social_posts SET updated_at=? WHERE post_id=?",
                (storage._now(), post_id),
            )
    return get_post(post_id, user_id)


def delete_post(user_id: str, post_id: str) -> bool:
    with storage.conn() as connection:
        cursor = connection.execute(
            "DELETE FROM social_posts WHERE post_id=? AND user_id=?",
            (post_id, user_id),
        )
    return cursor.rowcount > 0


_POST_SELECT = """SELECT p.post_id,p.body,p.created_at,p.updated_at,p.format,p.link_url,
    p.project_id,p.artifact_ref,p.evidence_supported,p.evidence_total,
    p.like_count,p.comment_count,
    u.user_id,u.username,u.display_name,u.bio,u.is_demo,u.availability,
    pr.name AS project_name,pr.repository_url AS project_repository_url,
    p.publication_id,pub.kind AS pub_kind,pub.trust_level AS pub_trust,
    pub.ownership_verified AS pub_owner_verified,pub.supported AS pub_supported,
    pub.total AS pub_total,pub.title AS pub_title,
    (SELECT COUNT(*) FROM follows f WHERE f.followed_user_id=u.user_id) AS follower_count,
    EXISTS(SELECT 1 FROM follows f
        WHERE f.follower_user_id=:viewer AND f.followed_user_id=u.user_id) AS is_following,
    EXISTS(SELECT 1 FROM post_likes l
        WHERE l.post_id=p.post_id AND l.user_id=:viewer) AS liked_by_me,
    EXISTS(SELECT 1 FROM post_bookmarks b
        WHERE b.post_id=p.post_id AND b.user_id=:viewer) AS bookmarked_by_me
    FROM social_posts p
    JOIN users u ON u.user_id=p.user_id
    LEFT JOIN projects pr ON pr.project_id=p.project_id
    LEFT JOIN publications pub ON pub.publication_id=p.publication_id AND pub.revoked_at IS NULL"""


def _hydrate(connection, rows) -> list[dict]:
    """Turn joined post rows into API objects, batch-loading tags and tip totals."""
    ids = [row["post_id"] for row in rows]
    tags: dict[str, list[str]] = {pid: [] for pid in ids}
    tips: dict[str, list[int]] = {pid: [] for pid in ids}
    if ids:
        marks = ",".join("?" * len(ids))
        for r in connection.execute(
            f"SELECT post_id,tag FROM post_tags WHERE post_id IN ({marks}) ORDER BY tag", ids
        ):
            tags[r["post_id"]].append(r["tag"])
        # Wei amounts exceed SQLite's 64-bit ints when summed, so add them in Python.
        for r in connection.execute(
            f"SELECT post_id,amount_wei FROM verified_tips WHERE post_id IN ({marks})", ids
        ):
            tips[r["post_id"]].append(int(r["amount_wei"]))
    items = []
    for row in rows:
        pid = row["post_id"]
        project = None
        if row["project_id"] and row["project_name"] is not None:
            project = {
                "project_id": row["project_id"],
                "name": row["project_name"],
                "repository_url": row["project_repository_url"],
            }
        evidence = None
        if row["evidence_total"] is not None:
            evidence = {
                "artifact": row["artifact_ref"],
                "supported": row["evidence_supported"],
                "total": row["evidence_total"],
            }
        if row["pub_kind"] is not None:
            # The passport re-checked the text that was actually published, so it wins
            # over the earlier artifact snapshot when it found checkable statements.
            use_pub = row["pub_total"] > 0 or evidence is None
            evidence = {
                "artifact": row["artifact_ref"],
                "supported": row["pub_supported"] if use_pub else evidence["supported"],
                "total": row["pub_total"] if use_pub else evidence["total"],
                "publication_id": row["publication_id"],
                "kind": row["pub_kind"],
                "trust_level": row["pub_trust"],
                "ownership_verified": bool(row["pub_owner_verified"]),
                "title": row["pub_title"] or None,
            }
        items.append({
            "post_id": pid,
            "body": row["body"],
            "format": row["format"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "edited": row["updated_at"] is not None,
            "tags": tags[pid],
            "link_url": row["link_url"],
            "project": project,
            "evidence": evidence,
            "like_count": row["like_count"],
            "comment_count": row["comment_count"],
            "liked_by_me": bool(row["liked_by_me"]),
            "bookmarked_by_me": bool(row["bookmarked_by_me"]),
            "tip_count": len(tips[pid]),
            "tip_total_wei": str(sum(tips[pid])),
            "author": {
                "user_id": row["user_id"],
                "username": row["username"],
                "display_name": row["display_name"],
                "bio": row["bio"],
                "is_demo": bool(row["is_demo"]),
                "availability": row["availability"],
                "follower_count": row["follower_count"],
                "is_following": bool(row["is_following"]),
            },
        })
    return items


def get_post(post_id: str, viewer_id: str) -> dict:
    with storage.conn() as connection:
        rows = connection.execute(
            _POST_SELECT + " WHERE p.post_id=:post AND u.verified_at IS NOT NULL",
            {"viewer": viewer_id, "post": post_id},
        ).fetchall()
        if not rows:
            raise KeyError("Post not found.")
        return _hydrate(connection, rows)[0]


def list_posts(
    viewer_id: str,
    scope: str = "discover",
    author_username: str | None = None,
    tag: str | None = None,
    bookmarked: bool = False,
    sort: str = "new",
    limit: int = 30,
    offset: int = 0,
) -> list[dict]:
    """One query path for every feed.

    scope: 'following' (you + people you follow), 'discover' (everyone but you),
    'all' (everyone). `bookmarked` limits to the viewer's saved posts.
    """
    if not 1 <= limit <= 50 or offset < 0:
        raise ValueError("Feed pagination requires limit 1-50 and offset >= 0.")
    if scope not in {"following", "discover", "all"}:
        raise ValueError("scope must be following, discover, or all.")
    if sort not in {"new", "top"}:
        raise ValueError("sort must be 'new' or 'top'.")
    where = ["u.verified_at IS NOT NULL"]
    params: dict = {"viewer": viewer_id, "limit": limit, "offset": offset}
    if scope == "following":
        where.append(
            """(p.user_id=:viewer OR EXISTS(SELECT 1 FROM follows f
            WHERE f.follower_user_id=:viewer AND f.followed_user_id=p.user_id))"""
        )
    elif scope == "discover":
        where.append("p.user_id!=:viewer")
    if author_username:
        where.append("u.username=:author COLLATE NOCASE")
        params["author"] = author_username
    if tag:
        where.append("EXISTS(SELECT 1 FROM post_tags t WHERE t.post_id=p.post_id AND t.tag=:tag)")
        params["tag"] = tag.strip().lstrip("#").lower()
    if bookmarked:
        where.append(
            "EXISTS(SELECT 1 FROM post_bookmarks b WHERE b.post_id=p.post_id AND b.user_id=:viewer)"
        )
    order = (
        "(p.like_count + 2*p.comment_count) DESC,p.created_at DESC,p.post_id DESC"
        if sort == "top"
        else "p.created_at DESC,p.post_id DESC"
    )
    sql = f"{_POST_SELECT} WHERE {' AND '.join(where)} ORDER BY {order} LIMIT :limit OFFSET :offset"
    with storage.conn() as connection:
        return _hydrate(connection, connection.execute(sql, params).fetchall())


def get_feed(user_id: str, limit: int = 30, offset: int = 0) -> list[dict]:
    return list_posts(user_id, "following", limit=limit, offset=offset)


def get_discover_feed(user_id: str, limit: int = 30, offset: int = 0) -> list[dict]:
    return list_posts(user_id, "discover", limit=limit, offset=offset)
