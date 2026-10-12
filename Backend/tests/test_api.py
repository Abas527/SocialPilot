import uuid
from dataclasses import replace
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient

from api import main
from api.main import app
from core import pipeline, storage
from core.schemas import (
    EvidenceReference,
    GroundedFinding,
    LinkedInDraft,
    ProjectProfile,
    SourceDocument,
)


def _authenticated_client(monkeypatch) -> TestClient:
    client = TestClient(app)
    email = f"user-{uuid.uuid4().hex}@example.test"
    test_settings = replace(
        storage.settings,
        email_provider="smtp",
        brevo_api_key="",
        smtp_host="smtp.example.test",
        smtp_from="SocialPilot <noreply@example.test>",
        smtp_username="",
        smtp_password="",
        smtp_use_ssl=False,
        smtp_starttls=True,
        public_api_url="https://api.example.test",
        https_redirect_enabled=False,
    )
    monkeypatch.setattr(main, "settings", test_settings)
    monkeypatch.setattr(main.email_delivery, "settings", test_settings)
    delivered_tokens = []
    monkeypatch.setattr(
        main.email_delivery,
        "send_verification_email",
        lambda recipient, name, token: delivered_tokens.append(token),
    )
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "display_name": "Test User",
            "password": "correct horse battery staple",
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "verification_required"
    assert client.post(
        "/auth/verify-email", json={"token": delivered_tokens[0]}
    ).status_code == 200
    login = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "correct horse battery staple",
        },
    )
    assert login.status_code == 200
    client.headers.update({"Authorization": "Bearer " + login.json()["access_token"]})
    return client


def test_project_import_persists_rag_chunks_and_search_api(tmp_path, monkeypatch):
    db_path = str(tmp_path / "api.db")
    monkeypatch.setattr(storage, "settings", replace(storage.settings, db_path=db_path))
    client = _authenticated_client(monkeypatch)

    imported = client.post(
        "/projects/import",
        json={
            "pasted_readme": (
                "# Tiny Counter\n"
                "The counter stores its value in counter.txt.\n\n"
                "## Operations\n"
                "It supports increment and decrement."
            )
        },
    )

    assert imported.status_code == 200
    project_id = imported.json()["project_id"]
    rag_status = client.get(f"/projects/{project_id}/rag")
    assert rag_status.status_code == 200
    assert rag_status.json()["chunk_count"] >= 1

    monkeypatch.setattr(storage, "settings", replace(storage.settings, chunk_chars=8))
    reindexed = client.post(f"/projects/{project_id}/rag/reindex")
    assert reindexed.status_code == 200
    assert reindexed.json()["chunk_chars"] == 8
    assert reindexed.json()["chunk_count"] > rag_status.json()["chunk_count"]

    results = client.get(
        f"/projects/{project_id}/rag/search",
        params={"q": "counter stores value", "limit": 3},
    )
    assert results.status_code == 200
    assert results.json()[0]["path"] == "pasted/README.md"
    assert results.json()[0]["start_line"] == 2

    project = client.get(f"/projects/{project_id}")
    assert project.status_code == 200
    assert project.json()["documents"][0]["path"] == "pasted/README.md"


def test_project_api_validates_import_source_and_search_input(tmp_path, monkeypatch):
    db_path = str(tmp_path / "validation.db")
    monkeypatch.setattr(storage, "settings", replace(storage.settings, db_path=db_path))
    client = _authenticated_client(monkeypatch)

    assert client.post("/projects/import", json={}).status_code == 422
    assert client.post(
        "/projects/import",
        json={"repo_url": "https://github.com/a/b", "pasted_readme": "# readme"},
    ).status_code == 422
    assert client.get("/projects/missing/rag").status_code == 404
    assert client.get("/projects/missing/rag/search", params={"q": " "}).status_code == 404
    owned_project = client.post(
        "/projects/import", json={"pasted_readme": "# Search validation"}
    ).json()["project_id"]
    assert client.get(
        f"/projects/{owned_project}/rag/search", params={"q": " "}
    ).status_code == 422
    assert client.post(
        f"/projects/{owned_project}/workflow/run",
        json={"linkedin_angles": ["technical_lesson", "technical_lesson"]},
    ).status_code == 422
    assert client.post(f"/projects/{owned_project}/workflow/run", json={}).status_code == 422


def test_health_reports_database_readiness_and_migration_version(tmp_path, monkeypatch):
    db_path = str(tmp_path / "health.db")
    monkeypatch.setattr(storage, "settings", replace(storage.settings, db_path=db_path))

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"]["ready"] is True
    assert response.json()["database"]["schema_version"] == 14


def test_project_workflow_generates_persists_edits_and_exports_artifact(tmp_path, monkeypatch):
    db_path = str(tmp_path / "workflow.db")
    monkeypatch.setattr(storage, "settings", replace(storage.settings, db_path=db_path))
    client = _authenticated_client(monkeypatch)
    created = client.post(
        "/projects/import",
        json={
            "pasted_readme": (
                "# Tiny Counter\n"
                "The counter stores its value in counter.txt and supports increment."
            )
        },
    )
    project_id = created.json()["project_id"]
    initial_state = client.get(f"/projects/{project_id}/workflow")
    assert initial_state.status_code == 200
    assert initial_state.json()["analysis_available"] is False
    assert initial_state.json()["source_count"] == 1
    doc = SourceDocument(
        source_id="readme",
        path="README.md",
        content="The counter stores its value in counter.txt and supports increment.",
    )
    evidence = EvidenceReference(
        source_id=doc.source_id,
        path=doc.path,
        start_line=1,
        end_line=1,
        excerpt=doc.content,
    )
    profile = ProjectProfile(
        name="Tiny Counter",
        summary="The counter stores its value in counter.txt.",
        findings=[
            GroundedFinding(
                finding_id="finding-1",
                kind="summary",
                text="The counter stores its value in counter.txt.",
                evidence=[evidence],
                status="supported",
            )
        ],
    )
    def save_profile_for_workflow(pid):
        storage.save_profile(pid, profile.model_dump())
        return profile

    monkeypatch.setattr(pipeline, "run_analysis", save_profile_for_workflow)
    monkeypatch.setattr(
        pipeline,
        "_load",
        lambda pid: (
            {"project_id": pid, "name": "Tiny Counter", "repository_url": None},
            [doc],
            pipeline.Retriever([doc], use_embeddings=False),
        ),
    )
    def fake_generate_draft(profile, retriever, docs, angle, user_context="", post_format="standard"):
        if angle == "engineering_decision":
            raise pipeline.LLMError("No source-backed findings are available for this angle.")
        return LinkedInDraft(
            angle="technical_lesson",
            hook="The counter stores its value in counter.txt.",
            insight="",
            body="",
            takeaway="",
            claims=["The counter stores its value in counter.txt."],
        )

    monkeypatch.setattr(
        pipeline.generation, "generate_linkedin_draft", fake_generate_draft
    )
    monkeypatch.setattr(pipeline, "settings", replace(pipeline.settings, case_study_chunked=False))
    monkeypatch.setattr(
        pipeline.generation,
        "generate_case_study",
        lambda *args: main.CaseStudy(
            title="Tiny Counter",
            summary="The counter stores its value in counter.txt.",
            problem="",
            architecture="",
            implementation="",
            challenges="",
            results="",
            limitations="",
            future_work="",
        ),
    )

    response = client.post(
        f"/projects/{project_id}/workflow/run",
        json={
            "linkedin_angles": ["technical_lesson", "engineering_decision"],
            "include_case_study": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["outputs"]["linkedin"]["technical_lesson"]["status"] == "generated"
    assert response.json()["outputs"]["linkedin"]["engineering_decision"]["status"] == "failed"
    assert response.json()["outputs"]["case_study"]["status"] == "generated"
    final_state = client.get(f"/projects/{project_id}/workflow").json()
    assert final_state["analysis_available"] is True
    assert final_state["supported_finding_count"] == 1
    assert {item["artifact_type"] for item in final_state["artifacts"]} == {
        "linkedin:technical_lesson",
        "case_study",
    }
    artifacts = client.get(f"/projects/{project_id}/artifacts/case_study")
    assert artifacts.status_code == 200
    assert artifacts.json()["current"]["title"] == "Tiny Counter"

    saved = client.put(
        f"/projects/{project_id}/artifacts/case_study",
        json={**artifacts.json()["current"], "summary": "Edited summary."},
    )
    assert saved.status_code == 200
    edited = client.get(f"/projects/{project_id}/artifacts/case_study")
    assert edited.json()["generated"]["summary"] == "The counter stores its value in counter.txt."
    assert edited.json()["current"]["summary"] == "Edited summary."

    reverted = client.post(f"/projects/{project_id}/artifacts/case_study/revert")
    assert reverted.status_code == 200
    assert client.get(f"/projects/{project_id}/artifacts/case_study").json()["current"]["summary"] == (
        "The counter stores its value in counter.txt."
    )

    exported = client.post(f"/projects/{project_id}/artifacts/case_study/export/markdown")
    assert exported.status_code == 200
    assert "The counter stores its value in counter.txt." in exported.text


def test_artifact_edits_require_generated_artifact_and_valid_schema(tmp_path, monkeypatch):
    db_path = str(tmp_path / "artifact-validation.db")
    monkeypatch.setattr(storage, "settings", replace(storage.settings, db_path=db_path))
    client = _authenticated_client(monkeypatch)
    created = client.post(
        "/projects/import",
        json={"pasted_readme": "# Project\nA small project."},
    )
    project_id = created.json()["project_id"]

    missing = client.put(
        f"/projects/{project_id}/artifacts/case_study",
        json={"title": "Incomplete"},
    )
    assert missing.status_code == 422
    assert storage.get_project_artifact(project_id, "case_study") is None

    unknown = client.put(
        f"/projects/{project_id}/artifacts/case_study",
        json={
            "title": "A valid schema",
            "summary": "",
            "problem": "",
            "architecture": "",
            "implementation": "",
            "challenges": "",
            "results": "",
            "limitations": "",
            "future_work": "",
            "claims": [],
        },
    )
    assert unknown.status_code == 404


def test_workflow_without_saved_analysis_returns_conflict(tmp_path, monkeypatch):
    db_path = str(tmp_path / "unanalysed.db")
    monkeypatch.setattr(storage, "settings", replace(storage.settings, db_path=db_path))
    client = _authenticated_client(monkeypatch)
    created = client.post(
        "/projects/import",
        json={"pasted_readme": "# Project\nA small project."},
    )

    response = client.post(
        f"/projects/{created.json()['project_id']}/workflow/run",
        json={"linkedin_angles": ["technical_lesson"], "reanalyze": False},
    )

    assert response.status_code == 409
    assert "Analyze this project" in response.json()["detail"]


def test_sources_and_paginated_rag_chunks_endpoints(tmp_path, monkeypatch):
    db_path = str(tmp_path / "sources.db")
    monkeypatch.setattr(storage, "settings", replace(storage.settings, db_path=db_path))
    client = _authenticated_client(monkeypatch)
    created = client.post(
        "/projects/import",
        json={"pasted_readme": "# Counter\nStores a count."},
    )
    project_id = created.json()["project_id"]

    sources = client.get(f"/projects/{project_id}/sources")
    chunks = client.get(
        f"/projects/{project_id}/rag/chunks",
        params={"limit": 1, "offset": 0, "path": "pasted/README.md"},
    )

    assert sources.status_code == 200
    assert sources.json()[0]["path"] == "pasted/README.md"
    assert "content" not in sources.json()[0]
    assert chunks.status_code == 200
    assert chunks.json()["total"] >= 1
    assert chunks.json()["items"][0]["path"] == "pasted/README.md"


def test_delete_project_removes_project_documents_and_persisted_chunks(tmp_path, monkeypatch):
    db_path = str(tmp_path / "delete.db")
    monkeypatch.setattr(storage, "settings", replace(storage.settings, db_path=db_path))
    client = _authenticated_client(monkeypatch)
    created = client.post(
        "/projects/import",
        json={"pasted_readme": "# Counter\nStores a count."},
    )
    project_id = created.json()["project_id"]

    deleted = client.delete(f"/projects/{project_id}")

    assert deleted.status_code == 204
    assert client.get(f"/projects/{project_id}").status_code == 404
    assert storage.get_project_chunks(project_id) is None


def test_auth_registration_login_me_logout_and_invalid_credentials(tmp_path, monkeypatch):
    db_path = str(tmp_path / "auth-flow.db")
    monkeypatch.setattr(storage, "settings", replace(storage.settings, db_path=db_path))
    client = TestClient(app)
    test_settings = replace(
        storage.settings,
        email_provider="smtp",
        brevo_api_key="",
        smtp_host="smtp.example.test",
        smtp_from="SocialPilot <noreply@example.test>",
        smtp_username="",
        smtp_password="",
        smtp_use_ssl=False,
        smtp_starttls=True,
    )
    monkeypatch.setattr(main, "settings", test_settings)
    monkeypatch.setattr(main.email_delivery, "settings", test_settings)
    delivered_tokens = []
    monkeypatch.setattr(
        main.email_delivery,
        "send_verification_email",
        lambda recipient, name, token: delivered_tokens.append(token),
    )
    user_data = {
        "email": "Person@Example.test",
        "display_name": "Person",
        "password": "correct horse battery staple",
    }

    registered = client.post("/auth/register", json=user_data)
    assert registered.status_code == 201
    assert registered.json()["status"] == "verification_required"
    assert client.post(
        "/auth/login",
        json={"email": user_data["email"], "password": user_data["password"]},
    ).status_code == 403
    assert len(delivered_tokens) == 1
    assert client.get("/auth/verify-email").status_code == 200
    assert client.post(
        "/auth/verify-email", json={"token": delivered_tokens[0]}
    ).status_code == 200
    token = client.post(
        "/auth/login",
        json={"email": user_data["email"], "password": user_data["password"]},
    ).json()["access_token"]
    assert client.get("/auth/me").status_code == 401
    client.headers.update({"Authorization": "Bearer " + token})
    assert client.get("/auth/me").json()["email"] == "person@example.test"

    client.headers.pop("Authorization")
    logged_in = client.post(
        "/auth/login",
        json={"email": "PERSON@example.test", "password": user_data["password"]},
    )
    assert logged_in.status_code == 200
    assert client.post(
        "/auth/login", json={"email": user_data["email"], "password": "wrong"}
    ).status_code == 401
    assert client.post("/auth/register", json=user_data).status_code == 409

    client.headers.update(
        {"Authorization": "Bearer " + logged_in.json()["access_token"]}
    )
    assert client.post("/auth/logout").status_code == 204
    assert client.get("/auth/me").status_code == 401


def test_project_routes_require_auth_and_enforce_owner_isolation(tmp_path, monkeypatch):
    db_path = str(tmp_path / "authorization.db")
    monkeypatch.setattr(storage, "settings", replace(storage.settings, db_path=db_path))
    anonymous = TestClient(app)
    assert anonymous.get("/projects").status_code == 401
    assert anonymous.post(
        "/projects/import", json={"pasted_readme": "# Private"}
    ).status_code == 401

    owner = _authenticated_client(monkeypatch)
    created = owner.post(
        "/projects/import", json={"pasted_readme": "# Private\nOwner-only content."}
    )
    assert created.status_code == 200
    project_id = created.json()["project_id"]
    assert owner.get("/projects").json()[0]["project_id"] == project_id

    other_user = _authenticated_client(monkeypatch)
    assert other_user.get("/projects").json() == []
    assert other_user.get(f"/projects/{project_id}").status_code == 404
    assert other_user.get(f"/projects/{project_id}/rag").status_code == 404
    assert other_user.get(f"/projects/{project_id}/sources").status_code == 404
    assert other_user.delete(f"/projects/{project_id}").status_code == 404
    assert owner.get(f"/projects/{project_id}").status_code == 200


def test_auth_registration_validates_password_and_email():
    client = TestClient(app)
    assert client.post(
        "/auth/register",
        json={"email": "bad", "display_name": "Name", "password": "short"},
    ).status_code == 422


def test_registration_fails_closed_without_smtp(tmp_path, monkeypatch):
    db_path = str(tmp_path / "smtp-unconfigured.db")
    monkeypatch.setattr(storage, "settings", replace(storage.settings, db_path=db_path))
    test_settings = replace(
        main.settings,
        email_provider="smtp",
        brevo_api_key="",
        smtp_host="",
        smtp_from="noreply@example.test",
        public_api_url="https://api.example.test",
    )
    monkeypatch.setattr(main, "settings", test_settings)
    monkeypatch.setattr(main.email_delivery, "settings", test_settings)
    client = TestClient(app)

    response = client.post(
        "/auth/register",
        json={
            "email": "pending@example.test",
            "display_name": "Pending",
            "password": "correct horse battery staple",
        },
    )

    assert response.status_code == 503
    assert storage.get_user_by_email("pending@example.test", db_path=db_path) is None


def test_end_to_end_signup_verification_login_and_owned_project(tmp_path, monkeypatch):
    db_path = str(tmp_path / "end-to-end.db")
    monkeypatch.setattr(storage, "settings", replace(storage.settings, db_path=db_path))
    test_settings = replace(
        main.settings,
        email_provider="smtp",
        brevo_api_key="",
        smtp_host="smtp.example.test",
        smtp_from="SocialPilot <noreply@example.test>",
        smtp_username="",
        smtp_password="",
        smtp_use_ssl=False,
        smtp_starttls=True,
        public_api_url="https://socialpilot.example",
        https_redirect_enabled=False,
    )
    monkeypatch.setattr(main, "settings", test_settings)
    monkeypatch.setattr(main.email_delivery, "settings", test_settings)
    sent_messages = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            assert (host, port, timeout) == ("smtp.example.test", 587, 10)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def ehlo(self):
            pass

        def starttls(self, context):
            assert context is not None

        def send_message(self, message):
            sent_messages.append(message)

    monkeypatch.setattr(main.email_delivery.smtplib, "SMTP", FakeSMTP)
    client = TestClient(app)
    credentials = {
        "email": "flow@example.test",
        "display_name": "Flow User",
        "password": "correct horse battery staple",
    }
    registration = client.post("/auth/register", json=credentials)
    assert registration.status_code == 201
    assert registration.json()["status"] == "verification_required"
    assert client.post(
        "/auth/login",
        json={"email": credentials["email"], "password": credentials["password"]},
    ).status_code == 403
    assert len(sent_messages) == 1
    assert sent_messages[0]["To"] == credentials["email"]

    verify_link = next(
        line.strip()
        for line in sent_messages[0].get_content().splitlines()
        if line.startswith("https://socialpilot.example/")
    )
    verify_url = urlsplit(verify_link)
    first_token = parse_qs(verify_url.fragment)["token"][0]
    assert verify_url.path == "/auth/verify-email"
    assert first_token not in verify_url.query
    page = client.get(verify_url.path)
    assert page.status_code == 200
    assert "Verify email" in page.text
    assert "no-store" in page.headers["cache-control"]

    resent = client.post(
        "/auth/resend-verification", json={"email": credentials["email"]}
    )
    assert resent.status_code == 202
    assert len(sent_messages) == 2
    assert client.post(
        "/auth/verify-email", json={"token": first_token}
    ).status_code == 400
    second_link = next(
        line.strip()
        for line in sent_messages[1].get_content().splitlines()
        if line.startswith("https://socialpilot.example/")
    )
    token = parse_qs(urlsplit(second_link).fragment)["token"][0]
    assert client.post("/auth/verify-email", json={"token": token}).status_code == 200
    assert client.post("/auth/verify-email", json={"token": token}).status_code == 400

    login = client.post(
        "/auth/login",
        json={"email": credentials["email"], "password": credentials["password"]},
    )
    assert login.status_code == 200
    client.headers.update({"Authorization": "Bearer " + login.json()["access_token"]})
    assert client.get("/auth/me").json()["email"] == credentials["email"]
    imported = client.post(
        "/projects/import",
        json={"pasted_readme": "# Verified project\nOnly its owner can access it."},
    )
    assert imported.status_code == 200
    project_id = imported.json()["project_id"]
    assert client.get(f"/projects/{project_id}").status_code == 200
    assert client.get(f"/projects/{project_id}/rag").status_code == 200
    search = client.get(
        f"/projects/{project_id}/rag/search",
        params={"q": "owner can access", "limit": 3},
    )
    assert search.status_code == 200
    assert search.json()[0]["path"] == "pasted/README.md"
    assert [p["project_id"] for p in client.get("/projects").json()] == [project_id]
    assert client.post("/auth/logout").status_code == 204
    assert client.get("/projects").status_code == 401


def test_https_redirect_and_hsts_headers(tmp_path, monkeypatch):
    db_path = str(tmp_path / "https.db")
    monkeypatch.setattr(storage, "settings", replace(storage.settings, db_path=db_path))
    monkeypatch.setattr(
        main,
        "settings",
        replace(main.settings, https_redirect_enabled=True, hsts_max_age=123),
    )
    client = TestClient(app)
    secure_client = TestClient(app, base_url="https://testserver")

    redirect = client.get("/health", follow_redirects=False)
    secure = secure_client.get("/health")

    assert redirect.status_code == 307
    assert redirect.headers["location"] == "https://testserver/health"
    assert secure.status_code == 200
    assert secure.headers["strict-transport-security"] == (
        "max-age=123; includeSubDomains"
    )
