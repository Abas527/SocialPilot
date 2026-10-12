"""In-app notifications for follows, likes, comments and verified tips."""
import uuid

from core import storage


def notify(
    connection,
    user_id: str,
    actor_user_id: str,
    type_: str,
    post_id: str | None = None,
    ref_id: str | None = None,
) -> None:
    """Insert a notification inside the caller's transaction (no self-notifications)."""
    if user_id == actor_user_id:
        return
    connection.execute(
        """INSERT INTO notifications
        (notification_id,user_id,actor_user_id,type,post_id,ref_id,created_at,read_at)
        VALUES(?,?,?,?,?,?,?,NULL)""",
        (uuid.uuid4().hex, user_id, actor_user_id, type_, post_id, ref_id, storage._now()),
    )


def list_notifications(
    user_id: str, limit: int = 30, offset: int = 0, unread_only: bool = False
) -> list[dict]:
    if not 1 <= limit <= 50 or offset < 0:
        raise ValueError("Pagination requires limit 1-50 and offset >= 0.")
    sql = """SELECT n.notification_id,n.type,n.post_id,n.ref_id,n.created_at,n.read_at,
        a.user_id AS actor_id,a.username AS actor_username,
        a.display_name AS actor_display_name,
        substr(p.body,1,140) AS post_excerpt
        FROM notifications n
        JOIN users a ON a.user_id=n.actor_user_id
        LEFT JOIN social_posts p ON p.post_id=n.post_id
        WHERE n.user_id=?"""
    if unread_only:
        sql += " AND n.read_at IS NULL"
    sql += " ORDER BY n.created_at DESC,n.notification_id DESC LIMIT ? OFFSET ?"
    with storage.conn() as connection:
        rows = connection.execute(sql, (user_id, limit, offset)).fetchall()
    return [
        {
            "notification_id": r["notification_id"],
            "type": r["type"],
            "post_id": r["post_id"],
            "post_excerpt": r["post_excerpt"],
            "ref_id": r["ref_id"],
            "created_at": r["created_at"],
            "read": r["read_at"] is not None,
            "actor": {
                "user_id": r["actor_id"],
                "username": r["actor_username"],
                "display_name": r["actor_display_name"],
            },
        }
        for r in rows
    ]


def unread_count(user_id: str) -> int:
    with storage.conn() as connection:
        return connection.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id=? AND read_at IS NULL",
            (user_id,),
        ).fetchone()[0]


def mark_read(user_id: str, notification_ids: list[str] | None = None) -> int:
    """Mark the given notifications (or all, when ids is None) as read."""
    now = storage._now()
    with storage.conn() as connection:
        if notification_ids is None:
            cursor = connection.execute(
                "UPDATE notifications SET read_at=? WHERE user_id=? AND read_at IS NULL",
                (now, user_id),
            )
        else:
            marks = ",".join("?" * len(notification_ids)) or "NULL"
            cursor = connection.execute(
                f"""UPDATE notifications SET read_at=?
                WHERE user_id=? AND read_at IS NULL AND notification_id IN ({marks})""",
                (now, user_id, *notification_ids),
            )
    return cursor.rowcount
