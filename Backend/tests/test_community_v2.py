from dataclasses import replace
from decimal import Decimal

from eth_account import Account

from config import settings as default_settings
from core import storage, tipping
from tests.test_social_tipping import _client, _link_wallet


def _two_users(monkeypatch, tmp_path):
    db = str(tmp_path / "v2.db")
    alice = _client(monkeypatch, db)
    bob = _client(monkeypatch, db)
    alice.put("/social/profile", json={"username": "alice_dev"})
    bob.put("/social/profile", json={"username": "bob_dev"})
    return db, alice, bob


def test_rich_post_tags_markdown_link_and_validation(tmp_path, monkeypatch):
    _, alice, bob = _two_users(monkeypatch, tmp_path)
    created = alice.post(
        "/social/posts",
        json={
            "body": "Shipped **v1**:\n```py\nprint('hi')\n```",
            "format": "markdown",
            "tags": ["#Python", "fastapi", "python"],
            "link_url": "https://github.com/me/repo",
        },
    )
    assert created.status_code == 201
    post = created.json()
    assert post["format"] == "markdown"
    assert post["tags"] == ["fastapi", "python"]  # normalized, de-duplicated
    assert post["like_count"] == 0 and post["tip_total_wei"] == "0"
    assert post["edited"] is False

    assert alice.post("/social/posts", json={"body": "x", "tags": ["bad tag!"]}).status_code == 422
    assert alice.post("/social/posts", json={"body": "x", "link_url": "javascript:alert(1)"}).status_code == 422
    assert alice.post("/social/posts", json={"body": "x", "tags": list("abcdef")}).status_code == 422

    assert [p["post_id"] for p in bob.get("/social/posts?tag=Python").json()] == [post["post_id"]]
    assert bob.get("/social/posts?tag=rust").json() == []
    assert bob.get("/social/trending/tags").json()[0]["post_count"] == 1
    assert bob.get("/social/profiles/alice_dev/posts").json()[0]["post_id"] == post["post_id"]

    edited = alice.put(f"/social/posts/{post['post_id']}", json={"body": "Edited", "tags": ["go"]})
    assert edited.json()["edited"] is True and edited.json()["tags"] == ["go"]
    assert bob.put(f"/social/posts/{post['post_id']}", json={"body": "hax"}).status_code == 404


def test_like_bookmark_comment_counters_and_notifications(tmp_path, monkeypatch):
    _, alice, bob = _two_users(monkeypatch, tmp_path)
    post_id = alice.post("/social/posts", json={"body": "Hello devs"}).json()["post_id"]

    assert bob.post(f"/social/posts/{post_id}/like").json() == {"liked": True, "like_count": 1}
    assert bob.post(f"/social/posts/{post_id}/like").json()["like_count"] == 1  # idempotent
    assert bob.post(f"/social/posts/{post_id}/bookmark").json()["bookmarked"] is True
    comment = bob.post(f"/social/posts/{post_id}/comments", json={"body": "Nice!"})
    assert comment.status_code == 201
    assert alice.post(f"/social/posts/{post_id}/like").json()["like_count"] == 2

    seen_by_bob = bob.get(f"/social/posts/{post_id}").json()
    assert seen_by_bob["liked_by_me"] and seen_by_bob["bookmarked_by_me"]
    assert seen_by_bob["like_count"] == 2 and seen_by_bob["comment_count"] == 1
    assert [p["post_id"] for p in bob.get("/social/bookmarks").json()] == [post_id]
    assert bob.get(f"/social/posts/{post_id}/comments").json()[0]["body"] == "Nice!"

    # Alice is notified of the like and comment, not of her own like.
    assert alice.get("/notifications/unread-count").json() == {"unread": 2}
    kinds = sorted(n["type"] for n in alice.get("/notifications").json())
    assert kinds == ["comment", "like"]
    assert alice.post("/notifications/read", json={}).json() == {"marked": 2}
    assert alice.get("/notifications/unread-count").json() == {"unread": 0}

    assert bob.delete(f"/social/posts/{post_id}/like").json() == {"liked": False, "like_count": 1}
    cid = comment.json()["comment_id"]
    assert alice.delete(f"/social/comments/{cid}").status_code == 204  # post owner may moderate
    assert alice.get(f"/social/posts/{post_id}").json()["comment_count"] == 0
    assert bob.post(f"/social/posts/{post_id}/comments", json={"body": "  "}).status_code == 422
    assert bob.post("/social/posts/" + "0" * 32 + "/like").status_code == 404


def test_follow_notification_profile_fields_and_follow_lists(tmp_path, monkeypatch):
    _, alice, bob = _two_users(monkeypatch, tmp_path)
    profile = alice.put(
        "/social/profile",
        json={"skills": ["Python", "#Rust"], "timezone": "Asia/Kathmandu", "availability": "open_to_work"},
    )
    assert profile.status_code == 200
    assert profile.json()["skills"] == ["python", "rust"]
    assert alice.put("/social/profile", json={"timezone": "not a zone!!"}).status_code == 422
    assert alice.put("/social/profile", json={"availability": "busy"}).status_code == 422

    bob.post("/social/follow/alice_dev")
    assert alice.get("/notifications").json()[0]["type"] == "follow"
    assert [p["username"] for p in alice.get("/social/profiles/alice_dev/followers").json()] == ["bob_dev"]
    assert [p["username"] for p in bob.get("/social/profiles/bob_dev/following").json()] == ["alice_dev"]
    assert bob.get("/social/profiles/alice_dev").json()["availability"] == "open_to_work"


def test_post_can_carry_project_and_evidence_snapshot(tmp_path, monkeypatch):
    db, alice, bob = _two_users(monkeypatch, tmp_path)
    alice_id = alice.get("/auth/me").json()["user_id"]
    pid = storage.create_project(
        "My repo", "https://github.com/me/repo", None,
        [{"source_id": "s1", "path": "README.md", "content": "# hi", "source_url": None}],
        db_path=db, owner_user_id=alice_id,
    )
    storage.save_artifact(
        pid, "case_study",
        {"title": "T", "verified_claims": [
            {"text": "a", "status": "supported"},
            {"text": "b", "status": "supported"},
            {"text": "c", "status": "needs_review"},
        ]},
        db_path=db,
    )
    ok = alice.post("/social/posts", json={"body": "Case study!", "project_id": pid, "artifact_ref": "case_study"})
    assert ok.status_code == 201
    evidence = ok.json()["evidence"]
    assert {k: evidence[k] for k in ("artifact", "supported", "total")} == {
        "artifact": "case_study", "supported": 2, "total": 3,  # earlier artifact snapshot
    }
    assert evidence["publication_id"] and evidence["trust_level"] == "notes"  # no pinned commit
    assert ok.json()["project"]["name"] == "My repo"

    # Another user cannot attach someone else's project; unknown artifacts are rejected.
    assert bob.post("/social/posts", json={"body": "x", "project_id": pid}).status_code == 404
    missing = alice.post("/social/posts", json={"body": "x", "project_id": pid, "artifact_ref": "linkedin:technical_lesson"})
    assert missing.status_code == 422
    assert alice.post("/social/posts", json={"body": "x", "artifact_ref": "case_study"}).status_code == 422


def test_tip_attached_to_post_updates_totals_and_notifies(tmp_path, monkeypatch):
    db, alice, bob = _two_users(monkeypatch, tmp_path)
    alice_wallet, bob_wallet = Account.create(), Account.create()
    _link_wallet(alice, alice_wallet)
    _link_wallet(bob, bob_wallet)
    post_id = alice.post("/social/posts", json={"body": "Tip me"}).json()["post_id"]

    monkeypatch.setattr(
        tipping, "settings",
        replace(default_settings, db_path=db, sepolia_rpc_url="https://rpc.example.test",
                sepolia_min_confirmations=2, tip_intent_ttl_minutes=30, tip_max_wei=10**18),
    )
    wei = int(Decimal("0.01") * tipping.WEI_PER_ETH)
    results = {
        "eth_chainId": "0xaa36a7",
        "eth_getTransactionByHash": {"from": bob_wallet.address, "to": alice_wallet.address,
                                     "value": hex(wei), "chainId": "0xaa36a7", "blockNumber": "0x64"},
        "eth_getTransactionReceipt": {"status": "0x1", "blockNumber": "0x64"},
        "eth_blockNumber": "0x65",
    }

    class Fake:
        def __init__(self, result): self.result = result
        def raise_for_status(self): pass
        def json(self): return {"jsonrpc": "2.0", "id": 1, "result": self.result}

    monkeypatch.setattr(tipping.httpx, "post", lambda url, json, timeout: Fake(results[json["method"]]))

    # Recipient is derived from the post; a mismatching username is refused.
    assert bob.post("/tips/prepare", json={"post_id": post_id, "recipient_username": "bob_dev", "amount_eth": "0.01"}).status_code == 409
    assert bob.post("/tips/prepare", json={"amount_eth": "0.01"}).status_code == 409
    assert bob.post("/tips/prepare", json={"post_id": post_id, "message": "x" * 141, "amount_eth": "0.01"}).status_code == 422
    prepared = bob.post("/tips/prepare", json={"post_id": post_id, "message": "Great post", "amount_eth": "0.01"})
    assert prepared.status_code == 201 and prepared.json()["to"] == alice_wallet.address

    tx = "0x" + "cd" * 32
    verified = bob.post(f"/tips/{prepared.json()['intent_id']}/verify", json={"tx_hash": tx})
    assert verified.status_code == 200 and verified.json()["post_id"] == post_id

    post = bob.get(f"/social/posts/{post_id}").json()
    assert post["tip_count"] == 1 and post["tip_total_wei"] == str(wei)
    supporters = bob.get(f"/social/posts/{post_id}/tips").json()
    assert supporters[0]["sender_username"] == "bob_dev" and supporters[0]["message"] == "Great post"
    assert bob.get("/tips/sent").json()[0]["recipient_username"] == "alice_dev"
    assert alice.get("/tips/received").json()[0]["message"] == "Great post"
    assert "tip" in [n["type"] for n in alice.get("/notifications").json()]
    assert alice.get("/config/chain").json()["chain_id"] == 11155111


def test_write_endpoints_are_rate_limited(tmp_path, monkeypatch):
    _, alice, _bob = _two_users(monkeypatch, tmp_path)
    limit = default_settings.write_rate_limit_per_min
    codes = [alice.post("/social/posts", json={"body": f"p{i}"}).status_code for i in range(limit + 1)]
    assert codes[0] == 201 and codes[-1] == 429
