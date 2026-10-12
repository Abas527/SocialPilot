"""Developer-community endpoints: posts, engagement, notifications, tips on posts."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.dependencies import require_auth
from config import settings
from core import engagement, notifications, ratelimit, social, tipping

router = APIRouter()
_write_limit = ratelimit.limit_by_user("write", settings.write_rate_limit_per_min)


class PostUpdateReq(BaseModel):
    body: str | None = Field(default=None, min_length=1, max_length=8000)
    tags: list[str] | None = Field(default=None, max_length=5)


class CommentReq(BaseModel):
    body: str = Field(min_length=1, max_length=1000)


class MarkReadReq(BaseModel):
    # Omit (or send null) to mark everything as read.
    notification_ids: list[str] | None = Field(default=None, max_length=100)


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc).strip("'\"")) from exc
    except social.SocialError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except tipping.TipError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


# ---- posts ------------------------------------------------------------------

@router.get("/social/posts")
def explore_posts(
    tag: str | None = Query(default=None, max_length=30),
    author: str | None = Query(default=None, max_length=30),
    scope: Literal["following", "discover", "all"] = "all",
    sort: Literal["new", "top"] = "new",
    limit: int = Query(default=30, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(require_auth),
):
    return _call(
        social.list_posts, user["user_id"], scope, author, tag, False, sort, limit, offset
    )


@router.get("/social/posts/{post_id}")
def get_post(post_id: str, user: dict = Depends(require_auth)):
    return _call(social.get_post, post_id, user["user_id"])


@router.put("/social/posts/{post_id}", dependencies=[Depends(_write_limit)])
def edit_post(post_id: str, req: PostUpdateReq, user: dict = Depends(require_auth)):
    if req.body is None and req.tags is None:
        raise HTTPException(status_code=422, detail="Provide body and/or tags to update.")
    return _call(social.update_post, user["user_id"], post_id, req.body, req.tags)


@router.get("/social/profiles/{username}/posts")
def profile_posts(
    username: str,
    limit: int = Query(default=30, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(require_auth),
):
    _call(social.get_profile_by_username, username, user["user_id"])  # 404 if unknown
    return _call(
        social.list_posts, user["user_id"], "all", username, None, False, "new", limit, offset
    )


@router.get("/social/profiles/{username}/followers")
def profile_followers(
    username: str,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(require_auth),
):
    return _call(social.list_follows, username, user["user_id"], "followers", limit, offset)


@router.get("/social/profiles/{username}/following")
def profile_following(
    username: str,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(require_auth),
):
    return _call(social.list_follows, username, user["user_id"], "following", limit, offset)


@router.get("/social/trending/tags")
def trending_tags(
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=10, ge=1, le=50),
    _user: dict = Depends(require_auth),
):
    return engagement.trending_tags(days, limit)


# ---- likes, bookmarks, comments ---------------------------------------------

@router.post("/social/posts/{post_id}/like", dependencies=[Depends(_write_limit)])
def like_post(post_id: str, user: dict = Depends(require_auth)):
    return _call(engagement.like, user["user_id"], post_id)


@router.delete("/social/posts/{post_id}/like")
def unlike_post(post_id: str, user: dict = Depends(require_auth)):
    return _call(engagement.unlike, user["user_id"], post_id)


@router.post("/social/posts/{post_id}/bookmark", dependencies=[Depends(_write_limit)])
def bookmark_post(post_id: str, user: dict = Depends(require_auth)):
    return _call(engagement.bookmark, user["user_id"], post_id)


@router.delete("/social/posts/{post_id}/bookmark")
def unbookmark_post(post_id: str, user: dict = Depends(require_auth)):
    return _call(engagement.unbookmark, user["user_id"], post_id)


@router.get("/social/bookmarks")
def my_bookmarks(
    limit: int = Query(default=30, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(require_auth),
):
    return _call(
        social.list_posts, user["user_id"], "all", None, None, True, "new", limit, offset
    )


@router.get("/social/posts/{post_id}/comments")
def post_comments(
    post_id: str,
    limit: int = Query(default=30, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    _user: dict = Depends(require_auth),
):
    return _call(engagement.list_comments, post_id, limit, offset)


@router.post(
    "/social/posts/{post_id}/comments", status_code=201, dependencies=[Depends(_write_limit)]
)
def comment_on_post(post_id: str, req: CommentReq, user: dict = Depends(require_auth)):
    return _call(engagement.add_comment, user["user_id"], post_id, req.body)


@router.delete("/social/comments/{comment_id}", status_code=204)
def remove_comment(comment_id: str, user: dict = Depends(require_auth)):
    if not engagement.delete_comment(user["user_id"], comment_id):
        raise HTTPException(status_code=404, detail="Comment not found.")
    return None


# ---- notifications ----------------------------------------------------------

@router.get("/notifications")
def list_notifications(
    unread_only: bool = False,
    limit: int = Query(default=30, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(require_auth),
):
    return notifications.list_notifications(user["user_id"], limit, offset, unread_only)


@router.get("/notifications/unread-count")
def unread_count(user: dict = Depends(require_auth)):
    return {"unread": notifications.unread_count(user["user_id"])}


@router.post("/notifications/read")
def mark_notifications_read(req: MarkReadReq, user: dict = Depends(require_auth)):
    return {"marked": notifications.mark_read(user["user_id"], req.notification_ids)}


# ---- tips -------------------------------------------------------------------

@router.get("/tips/sent")
def sent_tips(
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(require_auth),
):
    return tipping.list_sent_tips(user["user_id"], limit, offset)


@router.get("/social/posts/{post_id}/tips")
def post_tips(
    post_id: str,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    _user: dict = Depends(require_auth),
):
    return _call(tipping.list_post_tips, post_id, limit, offset)


@router.get("/config/chain")
def chain_config(_user: dict = Depends(require_auth)):
    """What the wallet UI needs to know: network, limits and confirmation depth."""
    return {
        "network": "Sepolia",
        "chain_id": tipping.SEPOLIA_CHAIN_ID,
        "asset": "ETH",
        "min_confirmations": settings.sepolia_min_confirmations,
        "max_tip_wei": str(settings.tip_max_wei),
        "tip_intent_ttl_minutes": settings.tip_intent_ttl_minutes,
        "max_tip_message_chars": tipping.MAX_TIP_MESSAGE_CHARS,
    }
