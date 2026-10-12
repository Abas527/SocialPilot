"""Authenticated community and testnet tipping endpoints."""
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.dependencies import require_auth
from config import settings
from core import demo, marketplace, ratelimit, social, tipping

router = APIRouter()


class ProfileUpdateReq(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=30)
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    bio: str | None = Field(default=None, max_length=500)
    skills: list[str] | None = Field(default=None, max_length=15)
    timezone: str | None = Field(default=None, max_length=64)
    availability: Literal["none", "open_to_work", "hiring", "open_to_collab"] | None = None


class PostReq(BaseModel):
    body: str = Field(min_length=1, max_length=8000)
    format: Literal["plain", "markdown"] = "plain"
    tags: list[str] = Field(default_factory=list, max_length=5)
    link_url: str | None = Field(default=None, max_length=2048)
    project_id: str | None = Field(default=None, max_length=64)
    artifact_ref: str | None = Field(default=None, max_length=64)


class WalletChallengeReq(BaseModel):
    address: str = Field(min_length=42, max_length=42)


class WalletVerifyReq(BaseModel):
    challenge_id: str = Field(min_length=32, max_length=32)
    signature: str = Field(min_length=130, max_length=132)


class TipPrepareReq(BaseModel):
    # Either name a recipient or tip a post (the post's author is the recipient).
    recipient_username: str | None = Field(default=None, min_length=3, max_length=30)
    post_id: str | None = Field(default=None, min_length=32, max_length=32)
    message: str | None = Field(default=None, max_length=140)
    amount_eth: Decimal = Field(gt=0, max_digits=19, decimal_places=18)


class TipVerifyReq(BaseModel):
    tx_hash: str = Field(min_length=66, max_length=66)


class MarketplaceListingReq(BaseModel):
    product_type: Literal["plugin", "library", "agent"]
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=2000)
    price_eth: Decimal = Field(gt=0, max_digits=19, decimal_places=18)
    delivery_url: str = Field(min_length=12, max_length=2048)


class MarketplacePurchaseVerifyReq(BaseModel):
    tx_hash: str = Field(min_length=66, max_length=66)


def _social_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except social.SocialError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except tipping.TipRPCError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except tipping.TipError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except marketplace.MarketplaceError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _marketplace_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except tipping.TipRPCError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except marketplace.MarketplaceError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/social/profile")
def my_profile(user: dict = Depends(require_auth)):
    return _social_call(social.get_profile_by_id, user["user_id"], user["user_id"])


@router.put("/social/profile")
def update_my_profile(
    req: ProfileUpdateReq,
    user: dict = Depends(require_auth),
):
    return _social_call(
        social.update_profile,
        user["user_id"],
        req.username,
        req.display_name,
        req.bio,
        req.skills,
        req.timezone,
        req.availability,
    )


@router.get("/social/profiles")
def discover_profiles(
    q: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(require_auth),
):
    return _social_call(
        social.list_profiles,
        user["user_id"],
        q,
        limit,
        offset,
    )


@router.get("/social/profiles/{username}")
def get_profile(username: str, user: dict = Depends(require_auth)):
    return _social_call(social.get_profile_by_username, username, user["user_id"])


@router.post("/social/follow/{username}")
def follow_profile(username: str, user: dict = Depends(require_auth)):
    return {
        "following": True,
        "created": _social_call(social.follow, user["user_id"], username),
    }


@router.delete("/social/follow/{username}")
def unfollow_profile(username: str, user: dict = Depends(require_auth)):
    return {
        "following": False,
        "removed": _social_call(social.unfollow, user["user_id"], username),
    }


@router.get("/social/feed")
def activity_feed(
    limit: int = Query(default=30, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(require_auth),
):
    return _social_call(social.get_feed, user["user_id"], limit, offset)


@router.get("/social/discover")
def discover_feed(
    limit: int = Query(default=30, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(require_auth),
):
    return _social_call(social.get_discover_feed, user["user_id"], limit, offset)


@router.post(
    "/social/posts", status_code=201,
    dependencies=[Depends(ratelimit.limit_by_user("write", settings.write_rate_limit_per_min))],
)
def publish_post(req: PostReq, user: dict = Depends(require_auth)):
    return _social_call(
        social.create_post,
        user["user_id"],
        req.body,
        req.format,
        req.tags,
        req.project_id,
        req.artifact_ref,
        req.link_url,
    )


@router.delete("/social/posts/{post_id}", status_code=204)
def remove_post(post_id: str, user: dict = Depends(require_auth)):
    if not social.delete_post(user["user_id"], post_id):
        raise HTTPException(status_code=404, detail="Post not found.")
    return None


@router.get("/demo/status")
def demo_seed_status(_user: dict = Depends(require_auth)):
    return {"enabled": settings.demo_seed_enabled}


@router.post("/demo/seed")
def seed_demo_content(_user: dict = Depends(require_auth)):
    if not settings.demo_seed_enabled:
        raise HTTPException(status_code=404, detail="Demo seed endpoint is disabled.")
    return demo.seed_demo_content()


@router.post("/wallet/challenge")
def wallet_challenge(
    req: WalletChallengeReq,
    user: dict = Depends(require_auth),
):
    return _social_call(
        tipping.start_wallet_challenge, user["user_id"], req.address
    )


@router.post("/wallet/verify")
def wallet_verify(req: WalletVerifyReq, user: dict = Depends(require_auth)):
    return _social_call(
        tipping.verify_wallet_challenge,
        user["user_id"],
        req.challenge_id,
        req.signature,
    )


@router.post("/tips/prepare", status_code=201)
def prepare_tip(req: TipPrepareReq, user: dict = Depends(require_auth)):
    return _social_call(
        tipping.prepare_tip,
        user["user_id"],
        req.recipient_username,
        str(req.amount_eth),
        req.post_id,
        req.message,
    )


@router.post("/tips/{intent_id}/verify")
def verify_tip(
    intent_id: str,
    req: TipVerifyReq,
    user: dict = Depends(require_auth),
):
    return _social_call(
        tipping.verify_tip, user["user_id"], intent_id, req.tx_hash
    )


@router.get("/tips/received")
def received_tips(
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(require_auth),
):
    return _social_call(
        tipping.list_received_tips, user["user_id"], limit, offset
    )


@router.get("/marketplace/listings")
def browse_marketplace(
    q: str | None = Query(default=None, max_length=100),
    product_type: Literal["plugin", "library", "agent"] | None = None,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    _user: dict = Depends(require_auth),
):
    return _marketplace_call(
        marketplace.list_listings, q, product_type, limit, offset
    )


@router.get("/marketplace/listings/{listing_id}")
def marketplace_listing(listing_id: str, _user: dict = Depends(require_auth)):
    listing = marketplace.get_listing(listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Marketplace listing not found.")
    return listing


@router.get("/marketplace/mine")
def my_marketplace_listings(user: dict = Depends(require_auth)):
    return _marketplace_call(marketplace.list_my_listings, user["user_id"])


@router.post("/marketplace/listings", status_code=201)
def create_marketplace_listing(
    req: MarketplaceListingReq,
    user: dict = Depends(require_auth),
):
    return _marketplace_call(
        marketplace.create_listing,
        user["user_id"],
        req.product_type,
        req.title,
        req.description,
        str(req.price_eth),
        req.delivery_url,
    )


@router.delete("/marketplace/listings/{listing_id}", status_code=204)
def deactivate_marketplace_listing(
    listing_id: str,
    user: dict = Depends(require_auth),
):
    if not _marketplace_call(
        marketplace.deactivate_listing, user["user_id"], listing_id
    ):
        raise HTTPException(status_code=404, detail="Marketplace listing not found.")
    return None


@router.post("/marketplace/listings/{listing_id}/purchase", status_code=201)
def prepare_marketplace_purchase(
    listing_id: str,
    user: dict = Depends(require_auth),
):
    return _marketplace_call(
        marketplace.prepare_purchase, user["user_id"], listing_id
    )


@router.post("/marketplace/purchases/{intent_id}/verify")
def verify_marketplace_purchase(
    intent_id: str,
    req: MarketplacePurchaseVerifyReq,
    user: dict = Depends(require_auth),
):
    return _marketplace_call(
        marketplace.verify_purchase,
        user["user_id"],
        intent_id,
        req.tx_hash,
    )


@router.get("/marketplace/purchases")
def my_marketplace_purchases(user: dict = Depends(require_auth)):
    return _marketplace_call(marketplace.list_my_purchases, user["user_id"])


@router.get("/marketplace/purchases/{sale_id}")
def marketplace_purchase(sale_id: str, user: dict = Depends(require_auth)):
    purchase = _marketplace_call(
        marketplace.get_purchase, user["user_id"], sale_id
    )
    if purchase is None:
        raise HTTPException(status_code=404, detail="Verified purchase not found.")
    return purchase
