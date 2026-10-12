import threading
import time
from dataclasses import replace

import pytest

from core import dev_ai, generation, jobs, storage
from core.llm import LLMError
from core.rag.retriever import Retriever
from core.schemas import (
    CommunityPost, EvidenceReference, GroundedFinding, ProjectProfile, SourceDocument,
)
from tests.test_social_tipping import _client


def _wait(client, job_id, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        job = client.get(f"/jobs/{job_id}").json()
        if job["status"] in {"succeeded", "failed", "cancelled"}:
            return job
        time.sleep(0.02)
    raise AssertionError("job did not finish")


@pytest.fixture(autouse=True)
def _fresh_pool():
    jobs.shutdown()
    yield
    jobs.shutdown()


def test_text_job_runs_in_background_and_validates_code_blocks(tmp_path, monkeypatch):
    client = _client(monkeypatch, str(tmp_path / "j.db"))
    original = "i built a thing\n```py\nprint('x')\n```"
    replies = iter([
        dev_ai.ImproveResult(text="I built a thing.", notes=["fixed caps"]),  # drops code -> retry
        dev_ai.ImproveResult(text="I built a thing.\n```py\nprint('x')\n```", notes=["fixed caps"]),
    ])
    monkeypatch.setattr(dev_ai, "complete_json", lambda prompt, model: next(replies))
    created = client.post("/jobs", json={"kind": "improve_post", "text": original, "goal": "clarity"})
    assert created.status_code == 202 and created.json()["status"] in {"queued", "running", "succeeded"}
    job = _wait(client, created.json()["job_id"])
    assert job["status"] == "succeeded" and job["progress"] == 100
    assert "print('x')" in job["result"]["text"] and job["result"]["changed"] is True


def test_improve_fails_cleanly_when_model_keeps_dropping_code(tmp_path, monkeypatch):
    client = _client(monkeypatch, str(tmp_path / "j.db"))
    monkeypatch.setattr(dev_ai, "complete_json", lambda p, m: dev_ai.ImproveResult(text="no code"))
    job = _wait(client, client.post("/jobs", json={"kind": "improve_post", "text": "a\n```x```"}).json()["job_id"])
    assert job["status"] == "failed" and "code blocks" in job["error"]


def test_tag_suggestions_are_normalized(tmp_path, monkeypatch):
    client = _client(monkeypatch, str(tmp_path / "j.db"))
    monkeypatch.setattr(dev_ai, "complete_json", lambda p, m: dev_ai.TagResult(tags=["#Python", "bad tag", "fastapi", "python"]))
    job = _wait(client, client.post("/jobs", json={"kind": "suggest_tags", "text": "FastAPI app"}).json()["job_id"])
    assert job["result"]["tags"] == ["python", "fastapi"]


def test_workflow_job_reports_progress_and_can_be_cancelled(tmp_path, monkeypatch):
    db = str(tmp_path / "j.db")
    client = _client(monkeypatch, db)
    uid = client.get("/auth/me").json()["user_id"]
    pid = storage.create_project("P", None, None,
        [{"source_id": "s", "path": "README.md", "content": "# P", "source_url": None}],
        db_path=db, owner_user_id=uid)
    gate, started = threading.Event(), threading.Event()
    seen = []

    def fake_workflow(project_id, angles, include_case_study, user_context, reanalyze, progress=None, post_format="standard"):
        progress(30, "step one"); seen.append(30); started.set()
        gate.wait(3)
        progress(60, "step two")  # raises JobCancelled when cancelled
        seen.append(60)
        return {"project_id": project_id, "outputs": {}}

    monkeypatch.setattr(jobs.pipeline, "run_workflow", fake_workflow)
    created = client.post("/jobs", json={"kind": "workflow", "project_id": pid, "angles": ["technical_lesson"]})
    assert created.status_code == 202
    jid = created.json()["job_id"]
    assert started.wait(3)
    running = client.get(f"/jobs/{jid}").json()
    assert running["status"] == "running" and running["progress"] == 30 and running["step"] == "step one"
    # one active job per project
    assert client.post("/jobs", json={"kind": "analyze", "project_id": pid}).status_code == 409
    assert client.post(f"/jobs/{jid}/cancel").json()["status"] == "cancelled"
    gate.set()
    time.sleep(0.2)
    assert client.get(f"/jobs/{jid}").json()["status"] == "cancelled"
    assert seen == [30]  # stopped at the checkpoint


def test_job_authorization_validation_and_limits(tmp_path, monkeypatch):
    db = str(tmp_path / "j.db")
    a = _client(monkeypatch, db)
    b = _client(monkeypatch, db)
    assert a.post("/jobs", json={"kind": "improve_post"}).status_code == 422
    assert a.post("/jobs", json={"kind": "linkedin", "project_id": "x" * 32}).status_code == 422
    assert a.post("/jobs", json={"kind": "analyze", "project_id": "nope"}).status_code == 404
    assert a.post("/jobs", json={"kind": "analyze"}).status_code == 422  # missing project
    monkeypatch.setattr(dev_ai, "complete_json", lambda p, m: dev_ai.TagResult(tags=["x1"]))
    jid = a.post("/jobs", json={"kind": "suggest_tags", "text": "hello"}).json()["job_id"]
    _wait(a, jid)
    assert b.get(f"/jobs/{jid}").status_code == 404 and b.post(f"/jobs/{jid}/cancel").status_code == 404
    monkeypatch.setattr(jobs, "settings", replace(jobs.settings, ai_daily_job_limit=1))
    assert a.post("/jobs", json={"kind": "suggest_tags", "text": "again"}).status_code == 429
    assert a.get("/jobs").json()[0]["job_id"] == jid


def test_recover_interrupted_marks_orphans_failed(tmp_path, monkeypatch):
    db = str(tmp_path / "j.db")
    client = _client(monkeypatch, db)
    uid = client.get("/auth/me").json()["user_id"]
    with storage.conn() as c:
        c.execute("INSERT INTO ai_jobs(job_id,user_id,kind,status,created_at) VALUES('j1',?,'suggest_tags','running','2026-01-01')", (uid,))
    assert jobs.recover_interrupted() == 1
    assert client.get("/jobs/j1").json()["status"] == "failed"


def _profile_and_docs():
    docs = [SourceDocument(source_id="s", path="README.md",
                           content="Tiny Counter stores a count in counter.txt and supports increment.")]
    ev = EvidenceReference(source_id="s", path="README.md", start_line=1, end_line=1, excerpt=docs[0].content)
    profile = ProjectProfile(name="Tiny Counter", summary="s", findings=[
        GroundedFinding(finding_id="f", kind="architecture", text="Stores a count in counter.txt.",
                        status="supported", evidence=[ev])])
    from core.rag.chunking import chunk_documents
    return profile, docs, Retriever(chunks=chunk_documents(docs, 1200))


def test_community_post_is_claim_checked_and_retried_when_unsupported(monkeypatch):
    profile, docs, retriever = _profile_and_docs()
    replies = iter([
        CommunityPost(body="Tiny Counter stores a count in `counter.txt`. It handles 10k users.", tags=["Python", "bad tag"]),
        CommunityPost(body="Tiny Counter stores a count in `counter.txt` and supports increment.", tags=["#python", "cli"]),
    ])
    monkeypatch.setattr(generation, "complete_json", lambda prompt, model: next(replies))
    post = generation.generate_community_post(profile, retriever, docs, "devlog")
    assert post.review_status == "preliminary_support"
    assert "10k" not in post.body
    assert post.tags == ["python", "cli"]
    with pytest.raises(LLMError):
        generation.generate_community_post(profile, retriever, docs, "nonsense")


def test_llm_retries_transient_errors_but_not_timeouts(monkeypatch):
    import httpx
    from core import llm
    monkeypatch.setattr(llm, "settings", replace(llm.settings, llm_retry_backoff_s=0, llm_max_retries=2))
    calls = []

    def flaky(url, *, json, timeout):
        calls.append(1)
        if len(calls) < 3:
            raise httpx.ConnectError("down")
        return type("R", (), {"raise_for_status": lambda s: None, "json": lambda s: {"message": {"content": "OK"}}})()

    monkeypatch.setattr(llm.httpx, "post", flaky)
    assert llm.complete("x") == "OK" and len(calls) == 3
    calls.clear()
    monkeypatch.setattr(llm.httpx, "post", lambda url, *, json, timeout: (calls.append(1), (_ for _ in ()).throw(httpx.ReadTimeout("slow")))[1])
    with pytest.raises(LLMError):
        llm.complete("x")
    assert len(calls) == 1
