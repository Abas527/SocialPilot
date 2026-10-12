"""Background AI jobs: create, poll, cancel."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator

from api.dependencies import require_auth
from config import settings
from core import jobs, ratelimit, storage
from core.generation import COMMUNITY_STYLES, POST_FORMATS
from core.schemas import Angle

router = APIRouter()
_ai_limit = ratelimit.limit_by_user("ai-jobs", settings.ai_rate_limit_per_min)

_Kind = Literal[
    "analyze", "post", "linkedin", "case_study", "case_study_section", "community_post", "workflow",
    "improve_post", "suggest_tags", "summarize_thread",
]


class JobReq(BaseModel):
    kind: _Kind
    project_id: str | None = Field(default=None, max_length=64)
    # project jobs
    angle: Angle | None = None
    angles: list[Angle] = Field(default_factory=list, max_length=3)
    include_case_study: bool = False
    reanalyze: bool = True
    user_context: str = Field(default="", max_length=4000)
    section: Literal[
        "summary", "problem", "architecture", "implementation", "challenges",
        "results", "limitations", "future_work",
    ] | None = None
    post_format: Literal["standard", "concise", "technical_walkthrough", "project_update"] = "standard"
    style: Literal["show_and_tell", "devlog", "til", "ask"] = "show_and_tell"
    # text jobs
    text: str | None = Field(default=None, max_length=8000)
    goal: Literal["clarity", "concise", "friendly", "technical"] = "clarity"
    post_id: str | None = Field(default=None, min_length=32, max_length=32)

    @model_validator(mode="before")
    @classmethod
    def alias_post_kind(cls, data):
        # "post" is the public name; "linkedin" stays as a backward-compatible alias.
        if isinstance(data, dict) and data.get("kind") == "post":
            data = {**data, "kind": "linkedin"}
        return data

    @model_validator(mode="after")
    def check_kind_inputs(self):
        if self.kind == "linkedin" and not self.angle:
            raise ValueError("post jobs require an angle.")
        if self.kind == "case_study_section" and not self.section:
            raise ValueError("case_study_section jobs require a section.")
        if self.kind == "workflow":
            if len(set(self.angles)) != len(self.angles):
                raise ValueError("angles must not contain duplicates.")
            if not self.angles and not self.include_case_study:
                raise ValueError("Request at least one angle or a case study.")
        if self.kind in {"improve_post", "suggest_tags"} and not (self.text and self.text.strip()):
            raise ValueError(f"{self.kind} jobs require text.")
        if self.kind == "summarize_thread" and not self.post_id:
            raise ValueError("summarize_thread jobs require post_id.")
        return self

    def params(self) -> dict:
        return {
            "angle": self.angle, "angles": self.angles,
            "include_case_study": self.include_case_study, "reanalyze": self.reanalyze,
            "user_context": self.user_context, "post_format": self.post_format,
            "style": self.style, "section": self.section, "text": self.text, "goal": self.goal, "post_id": self.post_id,
        }


@router.post("/jobs", status_code=202, dependencies=[Depends(_ai_limit)])
def create_job(req: JobReq, user: dict = Depends(require_auth)):
    if req.project_id:
        owner = storage.get_project_owner(req.project_id)
        if owner is None or owner["user_id"] != user["user_id"]:
            raise HTTPException(status_code=404, detail="Project not found.")
    try:
        return jobs.create_job(user["user_id"], req.kind, req.params(), req.project_id)
    except jobs.JobLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except jobs.JobError as exc:
        status = 422 if "needs a project_id" in str(exc) or "does not take" in str(exc) else 409
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.get("/jobs")
def list_jobs(
    project_id: str | None = Query(default=None, max_length=64),
    active_only: bool = False,
    limit: int = Query(default=20, ge=1, le=50),
    user: dict = Depends(require_auth),
):
    return jobs.list_jobs(user["user_id"], project_id, active_only, limit)


@router.get("/jobs/{job_id}")
def get_job(job_id: str, user: dict = Depends(require_auth)):
    try:
        return jobs.get_job(user["user_id"], job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found.") from exc


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str, user: dict = Depends(require_auth)):
    try:
        return jobs.cancel_job(user["user_id"], job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found.") from exc


@router.get("/ai/options")
def ai_options(_user: dict = Depends(require_auth)):
    """What the UI can offer: post formats, community styles and improve goals."""
    from core import dev_ai
    return {
        "post_formats": list(POST_FORMATS),
        "community_styles": list(COMMUNITY_STYLES),
        "improve_goals": list(dev_ai.GOALS),
    }
