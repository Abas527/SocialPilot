"""Evidence passports: publish, share to the community, and let anyone inspect/re-verify."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import require_auth, require_project_owner
from config import settings
from core import publications, ratelimit, social

router = APIRouter()
_write = ratelimit.limit_by_user("publish", settings.write_rate_limit_per_min)
_public_read = ratelimit.limit_by_ip("public-read", 60)
_public_reverify = ratelimit.limit_by_ip("public-reverify", 6)


class ShareCaseStudyReq(BaseModel):
    note: str = Field(default="", max_length=500)
    tags: list[str] = Field(default_factory=list, max_length=5)


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc).strip("'\"")) from exc
    except (publications.PublicationError, social.SocialError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---- author side --------------------------------------------------------------

@router.post("/projects/{pid}/share/case-study", status_code=201, dependencies=[Depends(_write)])
def share_case_study(pid: str, req: ShareCaseStudyReq, user: dict = Depends(require_project_owner)):
    """Freeze the case study with its evidence, then post a teaser to the community feed."""
    def run():
        publication = publications.publish_case_study(user["user_id"], pid)
        stored = publications.get_public(publication["publication_id"])
        body = publications.case_study_post_body(stored["content"], req.note)
        post = social.create_post(
            user["user_id"], body, "markdown", req.tags, pid, "case_study",
            None, publication["publication_id"],
        )
        return {"post": post, "publication": publication}

    return _call(run)


@router.post("/projects/{pid}/publications/case-study", status_code=201, dependencies=[Depends(_write)])
def publish_case_study_only(pid: str, user: dict = Depends(require_project_owner)):
    """Create a shareable evidence page without posting to the feed."""
    return _call(publications.publish_case_study, user["user_id"], pid)


@router.get("/projects/{pid}/publications")
def project_publications(pid: str, user: dict = Depends(require_project_owner)):
    return publications.list_for_project(user["user_id"], pid)


@router.delete("/publications/{publication_id}", status_code=204)
def unpublish(publication_id: str, user: dict = Depends(require_auth)):
    if not publications.revoke(user["user_id"], publication_id):
        raise HTTPException(status_code=404, detail="Publication not found.")
    return None


@router.get("/projects/{pid}/ownership")
def ownership(pid: str, _user: dict = Depends(require_project_owner)):
    return publications.ownership_status(pid)


@router.post("/projects/{pid}/ownership/start", dependencies=[Depends(_write)])
def ownership_start(pid: str, user: dict = Depends(require_project_owner)):
    return _call(publications.start_ownership, user["user_id"], pid)


@router.post("/projects/{pid}/ownership/check", dependencies=[Depends(_write)])
def ownership_check(pid: str, user: dict = Depends(require_project_owner)):
    return _call(publications.check_ownership, user["user_id"], pid)


# ---- public side (no login: this is what a recruiter opens) --------------------

@router.get("/public/publications/{publication_id}", dependencies=[Depends(_public_read)])
def public_publication(publication_id: str):
    try:
        return publications.get_public(publication_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Publication not found.") from exc
    except publications.PublicationError as exc:
        raise HTTPException(status_code=410, detail=str(exc)) from exc


@router.post("/public/publications/{publication_id}/reverify", dependencies=[Depends(_public_reverify)])
def public_reverify(publication_id: str):
    """Re-fetch the cited files from GitHub at the pinned commit and compare."""
    try:
        return publications.reverify(publication_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Publication not found.") from exc
    except publications.PublicationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
