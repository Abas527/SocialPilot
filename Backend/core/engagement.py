"""Likes, bookmarks, comments and trending tags for community posts."""
import uuid
from datetime import datetime, timedelta, timezone

from core import notifications, social, storage


def _require_post(connection, post_id: str):
    row = connection.execute(
        """SELECT p.post_id,p.user_id FROM social_posts p
        JOIN users u ON u.user_id=p.user_id
        WHERE p.post_id=? AND u.verified_at IS NOT NULL""",
        (post_id,),
    ).fetchone()
    if row is None:
        raise KeyError("Post not found.")
    return row


def like(user_id: str, post_id: str) -> dict:
    with storage.conn() as connection:
        post = _require_post(connection, post_id)
        cursor = connection.execute(
            "INSERT OR IGNORE INTO post_likes(post_id,user_id,created_at) VALUES(?,?,?)",
            (post_id, user_id, storage._now()),
        )
        if cursor.rowcount > 0:
            connection.execute(
                "UPDATE social_posts SET like_count=like_count+1 WHERE post_id=?", (post_id,)
            )
            notifications.notify(connection, post["user_id"], user_id, "like", post_id)
        count = connection.execute(
            "SELECT like_count FROM social_posts WHERE post_id=?", (post_id,)
        ).fetchone()[0]
    return {"liked": True, "like_count": count}


def unlike(user_id: str, post_id: str) -> dict:
    with storage.conn() as connection:
        _require_post(connection, post_id)
        cursor = connection.execute(
            "DELETE FROM post_likes WHERE post_id=? AND user_id=?", (post_id, user_id)
        )
        if cursor.rowcount > 0:
            connection.execute(
                "UPDATE social_posts SET like_count=MAX(like_count-1,0) WHERE post_id=?",
                (post_id,),
            )
        count = connection.execute(
            "SELECT like_count FROM social_posts WHERE post_id=?", (post_id,)
        ).fetchone()[0]
    return {"liked": False, "like_count": count}


def bookmark(user_id: str, post_id: str) -> dict:
    with storage.conn() as connection:
        _require_post(connection, post_id)
        connection.execute(
            "INSERT OR IGNORE INTO post_bookmarks(post_id,user_id,created_at) VALUES(?,?,?)",
            (post_id, user_id, storage._now()),
        )
    return {"bookmarked": True}


def unbookmark(user_id: str, post_id: str) -> dict:
    with storage.conn() as connection:
        _require_post(connection, post_id)
        connection.execute(
            "DELETE FROM post_bookmarks WHERE post_id=? AND user_id=?", (post_id, user_id)
        )
    return {"bookmarked": False}


def add_comment(user_id: str, post_id: str, body: str) -> dict:
    text = body.strip()
    if not text or len(text) > social.MAX_COMMENT_CHARS:
        raise social.SocialError(
            f"Comment must contain 1-{social.MAX_COMMENT_CHARS} characters."
        )
    comment_id = uuid.uuid4().hex
    created_at = storage._now()
    with storage.conn() as connection:
        post = _require_post(connection, post_id)
        author = connection.execute(
            "SELECT 1 FROM users WHERE user_id=? AND verified_at IS NOT NULL", (user_id,)
        ).fetchone()
        if author is None:
            raise KeyError("Verified user not found.")
        connection.execute(
            "INSERT INTO post_comments(comment_id,post_id,user_id,body,created_at) VALUES(?,?,?,?,?)",
            (comment_id, post_id, user_id, text, created_at),
        )
        connection.execute(
            "UPDATE social_posts SET comment_count=comment_count+1 WHERE post_id=?", (post_id,)
        )
        notifications.notify(
            connection, post["user_id"], user_id, "comment", post_id, comment_id
        )
    return get_comment(comment_id)


def get_comment(comment_id: str) -> dict:
    with storage.conn() as connection:
        row = connection.execute(
            """SELECT c.comment_id,c.post_id,c.body,c.created_at,
            u.user_id,u.username,u.display_name
            FROM post_comments c JOIN users u ON u.user_id=c.user_id
            WHERE c.comment_id=?""",
            (comment_id,),
        ).fetchone()
    if row is None:
        raise KeyError("Comment not found.")
    return _comment(row)


def _comment(row) -> dict:
    return {
        "comment_id": row["comment_id"],
        "post_id": row["post_id"],
        "body": row["body"],
        "created_at": row["created_at"],
        "author": {
            "user_id": row["user_id"],
            "username": row["username"],
            "display_name": row["display_name"],
        },
    }


def list_comments(post_id: str, limit: int = 30, offset: int = 0) -> list[dict]:
    if not 1 <= limit <= 50 or offset < 0:
        raise ValueError("Comment pagination requires limit 1-50 and offset >= 0.")
    with storage.conn() as connection:
        _require_post(connection, post_id)
        rows = connection.execute(
            """SELECT c.comment_id,c.post_id,c.body,c.created_at,
            u.user_id,u.username,u.display_name
            FROM post_comments c JOIN users u ON u.user_id=c.user_id
            WHERE c.post_id=? ORDER BY c.created_at,c.comment_id LIMIT ? OFFSET ?""",
            (post_id, limit, offset),
        ).fetchall()
    return [_comment(row) for row in rows]


def delete_comment(user_id: str, comment_id: str) -> bool:
    """A comment can be removed by its author or by the owner of the post."""
    with storage.conn() as connection:
        row = connection.execute(
            """SELECT c.post_id,c.user_id AS commenter,p.user_id AS post_owner
            FROM post_comments c JOIN social_posts p ON p.post_id=c.post_id
            WHERE c.comment_id=?""",
            (comment_id,),
        ).fetchone()
        if row is None or user_id not in (row["commenter"], row["post_owner"]):
            return False
        connection.execute("DELETE FROM post_comments WHERE comment_id=?", (comment_id,))
        connection.execute(
            "UPDATE social_posts SET comment_count=MAX(comment_count-1,0) WHERE post_id=?",
            (row["post_id"],),
        )
    return True


def trending_tags(days: int = 7, limit: int = 10) -> list[dict]:
    if not 1 <= days <= 90 or not 1 <= limit <= 50:
        raise ValueError("days must be 1-90 and limit 1-50.")
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with storage.conn() as connection:
        rows = connection.execute(
            """SELECT t.tag,COUNT(*) AS post_count
            FROM post_tags t JOIN social_posts p ON p.post_id=t.post_id
            WHERE p.created_at>=?
            GROUP BY t.tag ORDER BY post_count DESC,t.tag LIMIT ?""",
            (cutoff, limit),
        ).fetchall()
    return [{"tag": r["tag"], "post_count": r["post_count"]} for r in rows]
