import sqlite3

from core import migrations


def test_post_table_rebuild_keeps_children_and_allows_long_posts(tmp_path, monkeypatch):
    connection = sqlite3.connect(tmp_path / "m.db")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    full = migrations.MIGRATIONS

    monkeypatch.setattr(migrations, "MIGRATIONS", tuple(m for m in full if m[0] <= 11))
    assert migrations.migrate(connection) == 11
    now = "2026-01-01T00:00:00+00:00"
    cols = [r["name"] for r in connection.execute("PRAGMA table_info(users)")]
    values = {"user_id": "u1", "email": "a@x.test", "display_name": "A", "password_hash": "h",
              "created_at": now, "updated_at": now, "verified_at": now, "username": "user_a"}
    use = {c: v for c, v in values.items() if c in cols}
    connection.execute(
        f"INSERT INTO users({','.join(use)}) VALUES({','.join('?' * len(use))})", tuple(use.values())
    )
    connection.execute("INSERT INTO social_posts(post_id,user_id,body,created_at) VALUES('p1','u1','hello',?)", (now,))
    connection.execute("INSERT INTO post_tags VALUES('p1','python')")
    connection.execute("INSERT INTO post_likes VALUES('p1','u1',?)", (now,))
    connection.execute("INSERT INTO post_comments VALUES('c1','p1','u1','nice',?)", (now,))
    connection.commit()
    # The old CHECK rejects long posts.
    try:
        connection.execute(
            "INSERT INTO social_posts(post_id,user_id,body,created_at) VALUES('p2','u1',?,?)",
            ("x" * 5000, now),
        )
        raise AssertionError("old limit should reject")
    except sqlite3.IntegrityError:
        connection.rollback()

    monkeypatch.setattr(migrations, "MIGRATIONS", full)
    assert migrations.migrate(connection) == full[-1][0]
    assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    for table in ("post_tags", "post_likes", "post_comments", "social_posts"):
        assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 1, table
    connection.execute(
        "INSERT INTO social_posts(post_id,user_id,body,created_at) VALUES('p2','u1',?,?)",
        ("x" * 8000, now),
    )
    try:
        connection.execute(
            "INSERT INTO social_posts(post_id,user_id,body,created_at) VALUES('p3','u1',?,?)",
            ("x" * 8001, now),
        )
        raise AssertionError("new limit should reject")
    except sqlite3.IntegrityError:
        pass
