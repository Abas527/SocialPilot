"""Thin HTTP layer so any frontend (Streamlit, React, .NET) can use the same backend.
Run: uvicorn api.main:app --reload"""
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field, field_validator, model_validator

from api.dependencies import require_auth, require_project_owner
from api.engagement_routes import router as engagement_router
from api.job_routes import router as job_router
from api.publication_routes import router as publication_router
from api.feature_routes import router as feature_router
from config import settings
from core import authentication, email_delivery, export, generation, jobs, pipeline, ratelimit, storage
from core.ingestion import IngestionError
from core.llm import LLMError
from core.schemas import Angle, CaseStudy, CommunityPost, LinkedInDraft

@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        jobs.recover_interrupted()
    except Exception:  # noqa: BLE001 - never block startup on housekeeping
        pass
    yield
    jobs.shutdown()


app = FastAPI(title="SocialPilot AI", version="0.3.0", lifespan=lifespan)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,  # bearer tokens, not cookies
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        max_age=600,
    )

_auth_limit = ratelimit.limit_by_ip("auth", settings.auth_rate_limit_per_min)
_ai_limit = ratelimit.limit_by_user("ai", settings.ai_rate_limit_per_min)
_export_limit = ratelimit.limit_by_user("export", settings.export_rate_limit_per_min)


class RegisterReq(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    display_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        local, separator, domain = normalized.partition("@")
        if (
            not separator
            or not local
            or not domain
            or "." not in domain
            or any(char.isspace() for char in normalized)
        ):
            raise ValueError("Enter a valid email address.")
        return normalized

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Display name must not be blank.")
        return normalized


class LoginReq(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class EmailReq(BaseModel):
    email: str = Field(min_length=3, max_length=254)


class VerifyEmailReq(BaseModel):
    token: str = Field(min_length=20, max_length=512)


def _issue_session(user: dict) -> dict:
    if settings.auth_session_ttl_hours <= 0:
        raise RuntimeError("AUTH_SESSION_TTL_HOURS must be greater than zero.")
    token = authentication.create_access_token()
    expires_at = datetime.now(timezone.utc) + timedelta(
        hours=settings.auth_session_ttl_hours
    )
    storage.create_auth_session(user["user_id"], token, expires_at.isoformat())
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expires_at.isoformat(),
        "user": {
            "user_id": user["user_id"],
            "email": user["email"],
            "display_name": user["display_name"],
        },
    }


def _send_verification(user: dict) -> None:
    if settings.email_verification_ttl_hours <= 0:
        raise HTTPException(
            status_code=503,
            detail="Email verification is not configured correctly.",
        )
    token = authentication.create_access_token()
    expires_at = datetime.now(timezone.utc) + timedelta(
        hours=settings.email_verification_ttl_hours
    )
    storage.create_email_verification_token(
        user["user_id"], token, expires_at.isoformat()
    )
    try:
        email_delivery.send_verification_email(
            user["email"], user["display_name"], token
        )
    except email_delivery.EmailDeliveryError as exc:
        raise HTTPException(
            status_code=503,
            detail="Verification email could not be delivered. Try resending it later.",
        ) from exc


@app.post("/auth/register", status_code=201, dependencies=[Depends(_auth_limit)])
def register(req: RegisterReq):
    if not email_delivery.is_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "Email verification is unavailable. Check EMAIL_PROVIDER and "
                "the selected provider's configuration."
            ),
        )
    if settings.email_verification_ttl_hours <= 0:
        raise HTTPException(
            status_code=503,
            detail="Email verification is not configured correctly.",
        )
    try:
        user_id = storage.create_user(
            req.email, req.display_name, authentication.hash_password(req.password)
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    user = storage.get_user(user_id)
    if user is None:
        raise RuntimeError("Newly registered user could not be loaded.")
    _send_verification(user)
    return {
        "status": "verification_required",
        "message": "Check your email for a verification link before signing in.",
    }


@app.post("/auth/resend-verification", status_code=202, dependencies=[Depends(_auth_limit)])
def resend_verification(req: EmailReq):
    if not email_delivery.is_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "Email verification is unavailable. Check EMAIL_PROVIDER and "
                "the selected provider's configuration."
            ),
        )
    if settings.email_verification_ttl_hours <= 0:
        raise HTTPException(
            status_code=503,
            detail="Email verification is not configured correctly.",
        )
    user = storage.get_user_by_email(req.email)
    if user is not None and user["verified_at"] is None:
        _send_verification(user)
    return {
        "status": "accepted",
        "message": "If the account needs verification, a message will be sent.",
    }


@app.get("/auth/verify-email", response_class=HTMLResponse)
def verification_page():
    return HTMLResponse(
        f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Verify SocialPilot account</title>
<main>
  <h1>Verify your SocialPilot account</h1>
  <p id="status">Select the button to verify your email address.</p>
  <button id="verify" type="button">Verify email</button>
</main>
<script>
const token = new URLSearchParams(window.location.hash.slice(1)).get("token");
history.replaceState(null, "", window.location.pathname);
document.getElementById("verify").addEventListener("click", async () => {{
  if (!token) {{
    document.getElementById("status").textContent = "Verification link is missing its token.";
    return;
  }}
  const response = await fetch("/auth/verify-email", {{
    method: "POST",
    headers: {{"Content-Type": "application/json"}},
    body: JSON.stringify({{token}})
  }});
  document.getElementById("status").textContent = response.ok
    ? "Email verified. You can now sign in."
    : "This verification link is invalid, expired, or already used.";
  document.getElementById("verify").disabled = true;
}});
</script>
</html>""",
        headers={
            "Content-Security-Policy": (
                "default-src 'none'; script-src 'unsafe-inline'; "
                "connect-src 'self'; style-src 'unsafe-inline'; "
                "frame-ancestors 'none'; base-uri 'none'; object-src 'none'"
            ),
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer",
            "X-Frame-Options": "DENY",
        },
    )


@app.post("/auth/verify-email", dependencies=[Depends(_auth_limit)])
def verify_email(req: VerifyEmailReq):
    if not storage.verify_email_token(req.token):
        raise HTTPException(
            status_code=400,
            detail="Verification link is invalid, expired, or already used.",
        )
    return {"status": "verified", "message": "Email address verified. You can sign in."}


@app.post("/auth/login", dependencies=[Depends(_auth_limit)])
def login(req: LoginReq):
    user = storage.get_user_by_email(req.email)
    if (
        user is None
        or user["is_demo"]
        or not authentication.verify_password(req.password, user["password_hash"])
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user["verified_at"] is None:
        raise HTTPException(
            status_code=403,
            detail="Verify your email address before signing in.",
        )
    return _issue_session(user)


@app.get("/auth/me")
def me(user: dict = Depends(require_auth)):
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "display_name": user["display_name"],
    }


@app.post("/auth/logout", status_code=204)
def logout(user: dict = Depends(require_auth)):
    storage.revoke_auth_session_by_id(user["session_id"], user["user_id"])
    return Response(status_code=204)


@app.middleware("http")
async def enforce_https_and_hsts(request: Request, call_next):
    if settings.https_redirect_enabled and request.url.scheme != "https":
        secure_url = request.url.replace(scheme="https")
        return RedirectResponse(str(secure_url), status_code=307)
    response = await call_next(request)
    if request.url.scheme == "https" and settings.hsts_max_age > 0:
        response.headers["Strict-Transport-Security"] = (
            f"max-age={settings.hsts_max_age}; includeSubDomains"
        )
    return response


class ImportReq(BaseModel):
    repo_url: str | None = None
    pasted_readme: str | None = None

    @model_validator(mode="after")
    def validate_source(self):
        has_repo = bool(self.repo_url and self.repo_url.strip())
        has_readme = bool(self.pasted_readme and self.pasted_readme.strip())
        if has_repo == has_readme:
            raise ValueError("Provide exactly one of repo_url or pasted_readme.")
        return self


class GenReq(BaseModel):
    user_context: str = Field(default="", max_length=4000)
    post_format: Literal["standard", "concise", "technical_walkthrough", "project_update"] = "standard"


class WorkflowReq(BaseModel):
    linkedin_angles: list[Angle] = Field(default_factory=list, max_length=3)
    include_case_study: bool = False
    user_context: str = Field(default="", max_length=4000)
    reanalyze: bool = True

    @model_validator(mode="after")
    def validate_angles(self):
        if len(set(self.linkedin_angles)) != len(self.linkedin_angles):
            raise ValueError("linkedin_angles must not contain duplicates.")
        if not self.linkedin_angles and not self.include_case_study:
            raise ValueError("Request at least one post angle or a case study.")
        return self


def _guard(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except IngestionError as e:
        raise HTTPException(422, str(e))
    except LLMError as e:
        raise HTTPException(502, str(e))
    except KeyError as e:
        raise HTTPException(404, str(e))
    except pipeline.WorkflowError as e:
        raise HTTPException(409, str(e))
    except export.ExportError as e:
        raise HTTPException(503, str(e))


@app.get("/health")
def health():
    return {"status": "ok", "database": storage.database_status()}


@app.get("/projects")
def projects(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None, max_length=200),
    user: dict = Depends(require_auth),
):
    return storage.list_projects(
        limit=limit, offset=offset, query=q, owner_user_id=user["user_id"]
    )


@app.post("/projects/import")
def import_project(req: ImportReq, user: dict = Depends(require_auth)):
    return {
        "project_id": _guard(
            pipeline.import_project,
            req.repo_url,
            req.pasted_readme,
            owner_user_id=user["user_id"],
        )
    }


@app.get("/projects/{pid}")
def get_project(pid: str, _user: dict = Depends(require_project_owner)):
    p = storage.get_project(pid)
    if not p:
        raise HTTPException(404, "Project not found")
    return p


@app.get("/projects/{pid}/sources")
def project_sources(pid: str, _user: dict = Depends(require_project_owner)):
    sources = storage.list_project_documents(pid)
    if sources is None:
        raise HTTPException(404, "Project not found")
    return sources


@app.get("/projects/{pid}/workflow")
def workflow_status(pid: str, _user: dict = Depends(require_project_owner)):
    state = storage.get_project_workflow_state(pid)
    if state is None:
        raise HTTPException(404, "Project not found")
    state["rag"] = storage.ensure_project_index(pid)
    return state


@app.delete("/projects/{pid}", status_code=204)
def delete_project(pid: str, _user: dict = Depends(require_project_owner)):
    if not storage.delete_project(pid):
        raise HTTPException(404, "Project not found")
    return Response(status_code=204)


@app.get("/projects/{pid}/rag")
def rag_status(pid: str, _user: dict = Depends(require_project_owner)):
    index = storage.ensure_project_index(pid)
    if index is None:
        raise HTTPException(404, "Project not found")
    return index


@app.post("/projects/{pid}/rag/reindex")
def rag_reindex(pid: str, _user: dict = Depends(require_project_owner)):
    index = storage.rebuild_project_index(pid)
    if index is None:
        raise HTTPException(404, "Project not found")
    return index


@app.get("/projects/{pid}/rag/chunks")
def rag_chunks(
    pid: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    path: str | None = Query(default=None, max_length=500),
    _user: dict = Depends(require_project_owner),
):
    index = storage.ensure_project_index(pid)
    if index is None:
        raise HTTPException(404, "Project not found")
    page = storage.get_project_chunks_page(pid, limit=limit, offset=offset, path=path)
    if page is None:
        raise HTTPException(404, "Project not found")
    total, chunks = page
    return {
        "project_id": pid,
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [chunk.model_dump() for chunk in chunks],
    }


@app.get("/projects/{pid}/rag/search")
def rag_search(
    pid: str,
    q: str = Query(min_length=1, max_length=500),
    limit: int = Query(default=6, ge=1, le=20),
    _user: dict = Depends(require_project_owner),
):
    if not q.strip():
        raise HTTPException(422, "Search query must not be blank.")
    return _guard(pipeline.search_project, pid, q.strip(), limit)


@app.post("/projects/{pid}/analyze", dependencies=[Depends(_ai_limit)])
def analyze(pid: str, _user: dict = Depends(require_project_owner)):
    return _guard(pipeline.run_analysis, pid)


@app.post("/projects/{pid}/workflow/run", dependencies=[Depends(_ai_limit)])
def run_workflow(
    pid: str,
    req: WorkflowReq,
    _user: dict = Depends(require_project_owner),
):
    return _guard(
        pipeline.run_workflow,
        pid,
        req.linkedin_angles,
        req.include_case_study,
        req.user_context,
        req.reanalyze,
    )


@app.post("/projects/{pid}/post/{angle}", dependencies=[Depends(_ai_limit)])
@app.post("/projects/{pid}/linkedin/{angle}", dependencies=[Depends(_ai_limit)], include_in_schema=False)
def linkedin(
    pid: str,
    angle: str,
    req: GenReq,
    _user: dict = Depends(require_project_owner),
):
    if angle not in generation.ANGLES:
        raise HTTPException(400, f"angle must be one of {list(generation.ANGLES)}")
    return _guard(pipeline.run_linkedin, pid, angle, req.user_context, req.post_format)


@app.post("/projects/{pid}/case-study", dependencies=[Depends(_ai_limit)])
def case_study(pid: str, req: GenReq, _user: dict = Depends(require_project_owner)):
    return _guard(pipeline.run_case_study, pid, req.user_context)


@app.get("/projects/{pid}/artifacts/{artifact_type}")
def get_artifact(
    pid: str,
    artifact_type: str,
    _user: dict = Depends(require_project_owner),
):
    artifact = storage.get_project_artifact(pid, artifact_type)
    if artifact is None:
        if storage.get_project(pid) is None:
            raise HTTPException(404, "Project not found")
        raise HTTPException(404, "Artifact not found")
    return artifact


@app.put("/projects/{pid}/artifacts/{artifact_type}")
def save_edit(
    pid: str,
    artifact_type: str,
    content: dict,
    _user: dict = Depends(require_project_owner),
):
    try:
        if artifact_type == "case_study":
            validated_content = CaseStudy.model_validate(content).model_dump()
        elif artifact_type.startswith("linkedin:"):
            angle = artifact_type.partition(":")[2]
            if angle not in generation.ANGLES:
                raise HTTPException(422, "Unknown post artifact angle.")
            validated = LinkedInDraft.model_validate(content)
            if validated.angle != angle:
                raise HTTPException(422, "Post artifact angle does not match its key.")
            validated_content = validated.model_dump()
        elif artifact_type == "community_post":
            validated_content = CommunityPost.model_validate(content).model_dump()
        else:
            raise HTTPException(422, "Unsupported artifact type.")
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    _guard(storage.save_artifact, pid, artifact_type, validated_content, edited=True)
    return {"saved": True}


@app.post("/projects/{pid}/artifacts/{artifact_type}/revert")
def revert_edit(
    pid: str,
    artifact_type: str,
    _user: dict = Depends(require_project_owner),
):
    if artifact_type not in {"case_study", "community_post"} and not (
        artifact_type.startswith("linkedin:")
        and artifact_type.partition(":")[2] in generation.ANGLES
    ):
        raise HTTPException(422, "Unsupported artifact type.")
    reverted = _guard(storage.revert_artifact, pid, artifact_type)
    if not reverted:
        raise HTTPException(404, "Artifact not found")
    return {"reverted": True}


@app.post("/projects/{pid}/artifacts/case_study/export/markdown")
def project_case_study_markdown(
    pid: str,
    _user: dict = Depends(require_project_owner),
):
    project = storage.get_project(pid)
    if not project:
        raise HTTPException(404, "Project not found")
    artifact = storage.get_project_artifact(pid, "case_study")
    if artifact is None:
        raise HTTPException(404, "Case-study artifact not found")
    case_study = _guard(CaseStudy.model_validate, artifact["current"])
    markdown_text = export.case_study_to_markdown(
        case_study, project["repository_url"]
    )
    return Response(markdown_text, media_type="text/markdown")


@app.post("/projects/{pid}/artifacts/case_study/export/pdf")
def project_case_study_pdf(
    pid: str,
    _user: dict = Depends(require_project_owner),
):
    project = storage.get_project(pid)
    if not project:
        raise HTTPException(404, "Project not found")
    artifact = storage.get_project_artifact(pid, "case_study")
    if artifact is None:
        raise HTTPException(404, "Case-study artifact not found")
    case_study = _guard(CaseStudy.model_validate, artifact["current"])
    pdf_bytes = _guard(
        export.export_pdf, case_study, project["repository_url"]
    )
    return Response(pdf_bytes, media_type="application/pdf")


@app.post("/export/pdf", dependencies=[Depends(_export_limit)])
def pdf(cs: CaseStudy, repo_url: str | None = None):
    data = _guard(export.export_pdf, cs, repo_url)
    return Response(data, media_type="application/pdf")


@app.post("/export/markdown", dependencies=[Depends(_export_limit)])
def markdown(cs: CaseStudy, repo_url: str | None = None):
    return Response(export.case_study_to_markdown(cs, repo_url), media_type="text/markdown")


app.include_router(feature_router)
app.include_router(engagement_router)
app.include_router(job_router)
app.include_router(publication_router)
