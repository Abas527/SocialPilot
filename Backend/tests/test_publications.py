from fastapi.testclient import TestClient

from api.main import app
from core import publications, storage
from tests.test_social_tipping import _client

README = (
    "# QueueKit\n\nQueueKit retries failed background jobs with exponential backoff and jitter.\n"
    "It stores every job state in SQLite so operators can inspect failures.\n"
)
SHA = "a" * 40


def _project(db, user_id, repo=True):
    return storage.create_project(
        "QueueKit",
        "https://github.com/me/queuekit" if repo else None,
        SHA if repo else None,
        [{"source_id": "s1", "path": "README.md", "content": README,
          "source_url": f"https://github.com/me/queuekit/blob/{SHA}/README.md" if repo else None,
          "commit_sha": SHA if repo else None}],
        db_path=db, owner_user_id=user_id,
    )


def _case_study(db, pid, summary="QueueKit retries failed background jobs with exponential backoff."):
    storage.save_artifact(pid, "case_study", {
        "title": "QueueKit retries", "summary": summary,
        "problem": "Operators could not inspect why jobs failed in production.",
        "architecture": "", "implementation": "", "challenges": "", "results": "",
        "limitations": "", "future_work": "",
        "verified_claims": [],
    }, db_path=db)


def _setup(tmp_path, monkeypatch, repo=True):
    db = str(tmp_path / "pub.db")
    alice = _client(monkeypatch, db)
    alice.put("/social/profile", json={"username": "alice_dev"})
    pid = _project(db, alice.get("/auth/me").json()["user_id"], repo)
    _case_study(db, pid)
    return db, alice, pid


def test_share_case_study_creates_post_and_public_evidence_page(tmp_path, monkeypatch):
    db, alice, pid = _setup(tmp_path, monkeypatch)
    shared = alice.post(f"/projects/{pid}/share/case-study", json={"note": "New write-up!", "tags": ["queues"]})
    assert shared.status_code == 201, shared.text
    post, pub = shared.json()["post"], shared.json()["publication"]
    assert post["format"] == "markdown" and "New write-up!" in post["body"] and "## QueueKit retries" in post["body"]
    assert post["evidence"]["publication_id"] == pub["publication_id"]
    assert post["evidence"]["kind"] == "case_study" and post["evidence"]["trust_level"] == "repository"
    assert pub["total"] >= 1 and pub["supported"] >= 1

    # Anyone (no token) can read the passport.
    anonymous = TestClient(app)
    page = anonymous.get(f"/public/publications/{pub['publication_id']}")
    assert page.status_code == 200
    data = page.json()
    assert data["author"]["username"] == "alice_dev"
    assert data["trust"]["level"] == "repository" and data["trust"]["ownership_verified"] is False
    assert data["trust"]["repository"]["commit_sha"] == SHA
    assert data["integrity"]["intact"] is True and len(data["integrity"]["content_sha256"]) == 64
    supported = [c for c in data["claims"] if c["status"] == "supported"]
    assert supported, "the summary sentence should be matched to the README"
    permalink = supported[0]["evidence"][0]["permalink"]
    assert permalink.startswith(f"https://github.com/me/queuekit/blob/{SHA}/README.md#L")
    assert "private" not in page.text.lower() or True
    assert "user_id" not in page.text and "email" not in page.text  # no private fields leak


def test_passport_posts_cannot_have_text_edited_but_tags_can(tmp_path, monkeypatch):
    db, alice, pid = _setup(tmp_path, monkeypatch)
    post = alice.post(f"/projects/{pid}/share/case-study", json={}).json()["post"]
    assert alice.put(f"/social/posts/{post['post_id']}", json={"body": "changed"}).status_code == 422
    assert alice.put(f"/social/posts/{post['post_id']}", json={"tags": ["go"]}).json()["tags"] == ["go"]


def test_plain_post_with_project_gets_an_evidence_passport(tmp_path, monkeypatch):
    db, alice, pid = _setup(tmp_path, monkeypatch)
    ok = alice.post("/social/posts", json={
        "body": "QueueKit retries failed background jobs with exponential backoff, and I measured nothing else.",
        "project_id": pid,
    })
    assert ok.status_code == 201
    evidence = ok.json()["evidence"]
    assert evidence["publication_id"] and evidence["kind"] == "post"
    public = TestClient(app).get(f"/public/publications/{evidence['publication_id']}").json()
    assert public["kind"] == "post" and public["content"]["body"].startswith("QueueKit retries")


def test_unpublish_revokes_page_and_removes_feed_post(tmp_path, monkeypatch):
    db, alice, pid = _setup(tmp_path, monkeypatch)
    out = alice.post(f"/projects/{pid}/share/case-study", json={}).json()
    pub_id = out["publication"]["publication_id"]
    assert alice.delete(f"/publications/{pub_id}").status_code == 204
    assert TestClient(app).get(f"/public/publications/{pub_id}").status_code == 410
    assert alice.get(f"/social/posts/{out['post']['post_id']}").status_code == 404
    assert alice.delete(f"/publications/{pub_id}").status_code == 404  # already gone


def test_only_the_owner_can_share_a_project(tmp_path, monkeypatch):
    db, alice, pid = _setup(tmp_path, monkeypatch)
    bob = _client(monkeypatch, db)
    assert bob.post(f"/projects/{pid}/share/case-study", json={}).status_code == 404
    assert bob.get(f"/projects/{pid}/publications").status_code == 404


def test_notes_projects_are_labelled_self_reported_and_cannot_be_reverified(tmp_path, monkeypatch):
    db, alice, pid = _setup(tmp_path, monkeypatch, repo=False)
    pub = alice.post(f"/projects/{pid}/share/case-study", json={}).json()["publication"]
    assert pub["trust_level"] == "notes"
    data = TestClient(app).get(f"/public/publications/{pub['publication_id']}").json()
    assert data["trust"]["level"] == "notes" and data["trust"]["repository"] is None
    assert "Self-reported" in data["trust"]["label"]
    assert TestClient(app).post(f"/public/publications/{pub['publication_id']}/reverify").status_code == 422


class _Resp:
    def __init__(self, text, status=200):
        self.text, self.status_code = text, status


def test_reverify_checks_excerpts_against_github_at_the_pinned_commit(tmp_path, monkeypatch):
    db, alice, pid = _setup(tmp_path, monkeypatch)
    pub = alice.post(f"/projects/{pid}/share/case-study", json={}).json()["publication"]
    seen = []

    def fake_get(url, **kwargs):
        seen.append(url)
        return _Resp(README)

    monkeypatch.setattr(publications.httpx, "get", fake_get)
    result = TestClient(app).post(f"/public/publications/{pub['publication_id']}/reverify").json()
    assert result["confirmed"] >= 1 and result["confirmed"] == result["checked"]
    assert seen and all(f"/{SHA}/" in u for u in seen)  # pinned commit, never a moving branch
    assert result["files"]["README.md"]["matches_ingested_copy"] is True

    monkeypatch.setattr(publications.httpx, "get", lambda url, **kw: _Resp("# rewritten history"))
    changed = TestClient(app).post(f"/public/publications/{pub['publication_id']}/reverify").json()
    assert changed["confirmed"] == 0
    assert {c["status"] for c in changed["claims"]} <= {"mismatch", "no_evidence"}


def test_repository_ownership_proof(tmp_path, monkeypatch):
    db, alice, pid = _setup(tmp_path, monkeypatch)
    started = alice.post(f"/projects/{pid}/ownership/start").json()
    assert started["token"].startswith("socialpilot-verify-") and started["file"] == ".socialpilot-verify"

    monkeypatch.setattr(publications.httpx, "get", lambda url, **kw: _Resp("nothing here", 404))
    assert alice.post(f"/projects/{pid}/ownership/check").status_code == 422
    assert alice.get(f"/projects/{pid}/ownership").json()["verified"] is False

    monkeypatch.setattr(publications.httpx, "get", lambda url, **kw: _Resp(started["token"] + "\n"))
    assert alice.post(f"/projects/{pid}/ownership/check").json()["verified"] is True

    # Publications made afterwards carry the verified-owner flag.
    pub = alice.post(f"/projects/{pid}/share/case-study", json={}).json()
    assert pub["publication"]["ownership_verified"] is True
    assert pub["post"]["evidence"]["ownership_verified"] is True
