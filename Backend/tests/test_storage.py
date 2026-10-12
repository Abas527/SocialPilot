import hashlib
import sqlite3
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from core import migrations, storage
from core.pipeline import import_local_project


def test_fresh_database_runs_all_migrations(tmp_path):
    status = storage.database_status(str(tmp_path / "fresh.db"))

    assert status["ready"] is True
    assert status["engine"] == "sqlite"
    assert status["schema_version"] == 14
    assert status["migration_count"] == 14
    assert status["sqlite_version"]
    with storage.conn(str(tmp_path / "fresh.db")) as connection:
        assert connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='demo_payments'"
        ).fetchone() is None


def test_database_with_simulated_payment_migration_is_cleaned_up(tmp_path):
    db = str(tmp_path / "payment-migration.db")
    with sqlite3.connect(db) as connection:
        connection.execute(
            """CREATE TABLE schema_migrations(
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )"""
        )
        for version, name, statements in migrations.MIGRATIONS:
            if version > 9:
                break
            for statement in statements:
                connection.execute(statement)
            connection.execute(
                "INSERT INTO schema_migrations(version,name,applied_at) VALUES(?,?,?)",
                (version, name, "2025-01-01T00:00:00+00:00"),
            )
        connection.commit()

        assert migrations.migrate(connection) == 14
        assert connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='demo_payments'"
        ).fetchone() is None


def test_populated_legacy_database_migrates_without_losing_data(tmp_path):
    db = str(tmp_path / "legacy.db")
    with sqlite3.connect(db) as legacy:
        legacy.executescript(
            """
            CREATE TABLE projects(
                project_id TEXT PRIMARY KEY, name TEXT, repository_url TEXT,
                commit_sha TEXT, profile_json TEXT, created_at TEXT
            );
            CREATE TABLE source_documents(
                project_id TEXT, source_id TEXT, path TEXT, content TEXT,
                source_url TEXT, commit_sha TEXT, PRIMARY KEY(project_id,source_id)
            );
            CREATE TABLE artifacts(
                artifact_id TEXT PRIMARY KEY, project_id TEXT, artifact_type TEXT,
                generated_json TEXT, edited_json TEXT, created_at TEXT,
                updated_at TEXT, UNIQUE(project_id,artifact_type)
            );
            CREATE TABLE project_chunks(
                project_id TEXT NOT NULL, chunk_id TEXT NOT NULL, source_id TEXT NOT NULL,
                path TEXT NOT NULL, text TEXT NOT NULL, start_line INTEGER NOT NULL,
                end_line INTEGER NOT NULL, heading TEXT, source_url TEXT,
                PRIMARY KEY(project_id,chunk_id),
                FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE
            );
            CREATE TABLE project_rag_index(
                project_id TEXT PRIMARY KEY, chunk_chars INTEGER NOT NULL,
                chunk_count INTEGER NOT NULL, indexed_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE
            );
            INSERT INTO projects VALUES('legacy','Legacy','https://example.test/repo',
                'abc123','{"name":"Legacy"}','2025-01-01T00:00:00+00:00');
            INSERT INTO source_documents VALUES('legacy','readme','README.md',
                '# Legacy','https://example.test/repo/README.md','abc123');
            INSERT INTO artifacts VALUES('artifact','legacy','case_study',
                '{"title":"Saved"}','{"title":"Edited"}','2025-01-01','2025-01-02');
            INSERT INTO project_chunks VALUES('legacy','chunk','readme','README.md',
                '# Legacy',1,1,'Legacy','https://example.test/repo/README.md');
            INSERT INTO project_rag_index VALUES('legacy',800,1,'2025-01-01');
            """
        )

    project = storage.get_project("legacy", db_path=db)
    chunks = storage.get_project_chunks("legacy", db_path=db)
    index = storage.get_project_index("legacy", db_path=db)

    assert project["documents"][0]["content"] == "# Legacy"
    assert project["artifacts"]["case_study"]["edited"] == {"title": "Edited"}
    assert chunks and chunks[0].text == "# Legacy"
    assert index["chunk_count"] == 1
    with storage.conn(db) as migrated:
        assert migrated.execute("PRAGMA foreign_key_check").fetchall() == []
        migrated.execute("DELETE FROM projects WHERE project_id='legacy'")
        assert migrated.execute("SELECT COUNT(*) FROM source_documents").fetchone()[0] == 0
        assert migrated.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0] == 0
        assert migrated.execute("SELECT COUNT(*) FROM project_chunks").fetchone()[0] == 0
        assert migrated.execute("SELECT COUNT(*) FROM project_rag_index").fetchone()[0] == 0


def test_user_sessions_hash_tokens_and_support_revocation_and_expiry(tmp_path):
    db = str(tmp_path / "auth.db")
    user_id = storage.create_user(
        " User@Example.test ", "Example User", "password-hash", db_path=db
    )
    verification_token = "verify-email-before-session"
    storage.create_email_verification_token(
        user_id,
        verification_token,
        (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        db_path=db,
    )
    assert storage.verify_email_token(verification_token, db_path=db) is True
    assert storage.verify_email_token(verification_token, db_path=db) is False
    with storage.conn(db) as conn:
        verification_hash = conn.execute(
            "SELECT token_hash FROM email_verification_tokens WHERE user_id=?",
            (user_id,),
        ).fetchone()["token_hash"]
    assert verification_hash == hashlib.sha256(verification_token.encode()).hexdigest()
    assert verification_token not in verification_hash
    raw_token = "never-store-this-token"
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    session_id = storage.create_auth_session(
        user_id, raw_token, expires_at, db_path=db
    )

    assert session_id
    assert storage.get_user(user_id, db_path=db)["email"] == "user@example.test"
    assert "password_hash" not in storage.get_user(user_id, db_path=db)
    assert storage.get_active_auth_session(raw_token, db_path=db)["user_id"] == user_id
    assert storage.get_active_auth_session("wrong-token", db_path=db) is None
    with storage.conn(db) as conn:
        stored = conn.execute(
            "SELECT token_hash FROM auth_sessions WHERE session_id=?", (session_id,)
        ).fetchone()["token_hash"]
    assert stored == hashlib.sha256(raw_token.encode()).hexdigest()
    assert raw_token not in stored
    assert storage.revoke_auth_session(raw_token, db_path=db) is True
    assert storage.revoke_auth_session(raw_token, db_path=db) is False
    assert storage.get_active_auth_session(raw_token, db_path=db) is None


def test_expired_email_verification_token_cannot_verify_account(tmp_path):
    db = str(tmp_path / "expired-email-verification.db")
    user_id = storage.create_user("expiry@example.test", "Expiry", db_path=db)
    token = "expired-verification-link"
    storage.create_email_verification_token(
        user_id,
        token,
        (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        db_path=db,
    )
    with storage.conn(db) as conn:
        expired_created_at = datetime.now(timezone.utc) - timedelta(hours=2)
        conn.execute(
            """UPDATE email_verification_tokens SET created_at=?,expires_at=?
            WHERE user_id=?""",
            (
                expired_created_at.isoformat(),
                (expired_created_at + timedelta(hours=1)).isoformat(),
                user_id,
            ),
        )

    assert storage.verify_email_token(token, db_path=db) is False
    assert storage.get_user_by_email("expiry@example.test", db_path=db)["verified_at"] is None


def test_expired_sessions_duplicate_users_and_project_ownership(tmp_path):
    db = str(tmp_path / "ownership.db")
    user_id = storage.create_user("owner@example.test", "Owner", db_path=db)
    project_id = storage.create_project("Owned", None, None, [], db_path=db)
    storage.assign_project_owner(project_id, user_id, db_path=db)
    owner = storage.get_project_owner(project_id, db_path=db)

    assert owner["user_id"] == user_id
    assert [p["project_id"] for p in storage.list_projects(
        db_path=db, owner_user_id=user_id
    )] == [project_id]
    try:
        storage.create_user("OWNER@example.test", "Duplicate", db_path=db)
    except ValueError as exc:
        assert "already exists" in str(exc)
    else:
        raise AssertionError("Email uniqueness must be case-insensitive.")
    try:
        storage.create_auth_session(
            user_id,
            "expired-token",
            (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
            db_path=db,
        )
    except ValueError as exc:
        assert "future" in str(exc)
    else:
        raise AssertionError("Expired sessions must not be created.")

    with storage.conn(db) as conn:
        conn.execute("DELETE FROM users WHERE user_id=?", (user_id,))
        assert conn.execute("SELECT COUNT(*) FROM project_owners").fetchone()[0] == 0


def test_persistence_and_edit_separation(tmp_path):
    db = str(tmp_path / "t.db")
    pid = storage.create_project("P", None, None, [{"source_id": "1", "path": "README.md", "content": "x"}], db)
    storage.save_artifact(pid, "case_study", {"v": 1}, db_path=db)
    storage.save_artifact(pid, "case_study", {"v": 2}, edited=True, db_path=db)
    art = storage.get_project(pid, db)["artifacts"]["case_study"]
    assert art["generated"] == {"v": 1} and art["edited"] == {"v": 2}
    assert storage.list_projects(db)[0]["project_id"] == pid


def test_import_local_project_persists_ingested_documents(tmp_path, monkeypatch):
    db = str(tmp_path / "local-project.db")
    monkeypatch.setattr(storage, "settings", replace(storage.settings, db_path=db))
    fixture = Path(__file__).parent / "fixtures" / "tiny_counter"

    project_id = import_local_project(fixture)
    project = storage.get_project(project_id, db_path=db)

    assert project is not None
    assert project["name"] == "tiny_counter"
    assert project["repository_url"] is None
    assert {doc["path"] for doc in project["documents"]} >= {"README.md", "src/counter.py"}


def test_chunk_index_persists_and_legacy_projects_are_reindexed(tmp_path):
    db = str(tmp_path / "rag.db")
    pid = storage.create_project(
        "RAG",
        None,
        None,
        [{
            "source_id": "readme",
            "path": "README.md",
            "content": "# Counter\nThe counter stores values in counter.txt.",
        }],
        db_path=db,
    )
    original_chunks = storage.get_project_chunks(pid, db_path=db)
    assert original_chunks and "counter.txt" in original_chunks[0].text

    with storage.conn(db) as conn:
        conn.execute("DELETE FROM project_chunks WHERE project_id=?", (pid,))
        conn.execute("DELETE FROM project_rag_index WHERE project_id=?", (pid,))

    rebuilt = storage.ensure_project_index(pid, db_path=db)
    assert rebuilt is not None
    assert rebuilt["chunk_count"] == len(original_chunks)
    assert rebuilt["indexed_at"]
    assert storage.get_project_chunks(pid, db_path=db) == original_chunks


def test_edit_requires_generated_artifact_and_revert_restores_generated(tmp_path):
    db = str(tmp_path / "artifact-edit.db")
    pid = storage.create_project("P", None, None, [], db_path=db)

    try:
        storage.save_artifact(pid, "case_study", {"title": "Edited"}, edited=True, db_path=db)
    except KeyError as exc:
        assert "generate it before saving edits" in str(exc)
    else:
        raise AssertionError("An edit must not create an artifact without generated content.")

    storage.save_artifact(pid, "case_study", {"title": "Generated"}, db_path=db)
    storage.save_artifact(pid, "case_study", {"title": "Edited"}, edited=True, db_path=db)
    assert storage.get_project_artifact(pid, "case_study", db_path=db)["current"]["title"] == "Edited"
    assert storage.revert_artifact(pid, "case_study", db_path=db) is True
    artifact = storage.get_project_artifact(pid, "case_study", db_path=db)
    assert artifact["current"]["title"] == "Generated"
    assert artifact["edited"] is None


def test_project_listing_supports_pagination_and_name_filter(tmp_path):
    db = str(tmp_path / "project-list.db")
    projects = [
        storage.create_project(name, None, None, [], db_path=db)
        for name in ("Alpha", "Beta", "Alphabet")
    ]

    page = storage.list_projects(db_path=db, limit=1, offset=0)
    matches = storage.list_projects(db_path=db, query="Alpha")

    assert len(page) == 1
    assert [project["name"] for project in matches] == ["Alphabet", "Alpha"]
    assert set(projects) == {project["project_id"] for project in storage.list_projects(db_path=db)}
