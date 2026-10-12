from dataclasses import replace
from decimal import Decimal
import uuid

from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi.testclient import TestClient

from api import feature_routes, main
from api.main import app
from config import settings as default_settings
from core import marketplace, storage, tipping


def _client(monkeypatch, db_path: str) -> TestClient:
    monkeypatch.setattr(storage, "settings", replace(storage.settings, db_path=db_path))
    configured = replace(
        main.settings,
        db_path=db_path,
        smtp_host="smtp.test.local",
        smtp_from="SocialPilot <noreply@example.test>",
        smtp_username="",
        smtp_password="",
        smtp_use_ssl=False,
        smtp_starttls=True,
        public_api_url="https://socialpilot.example",
    )
    monkeypatch.setattr(main, "settings", configured)
    monkeypatch.setattr(main.email_delivery, "settings", configured)
    sent_tokens = []
    monkeypatch.setattr(
        main.email_delivery,
        "send_verification_email",
        lambda recipient, display_name, token: sent_tokens.append(token),
    )
    client = TestClient(app)
    email = f"{uuid.uuid4().hex}@example.test"
    registration = client.post(
        "/auth/register",
        json={
            "email": email,
            "display_name": "Builder",
            "password": "correct horse battery staple",
        },
    )
    assert registration.status_code == 201
    assert client.post(
        "/auth/verify-email", json={"token": sent_tokens[0]}
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


def _link_wallet(client: TestClient, account: Account) -> None:
    challenge = client.post(
        "/wallet/challenge", json={"address": account.address}
    )
    assert challenge.status_code == 200
    signature = Account.sign_message(
        encode_defunct(text=challenge.json()["message"]), private_key=account.key
    ).signature.hex()
    result = client.post(
        "/wallet/verify",
        json={
            "challenge_id": challenge.json()["challenge_id"],
            "signature": signature,
        },
    )
    assert result.status_code == 200


def test_social_profiles_following_and_explicit_activity_feed(tmp_path, monkeypatch):
    db_path = str(tmp_path / "social.db")
    first = _client(monkeypatch, db_path)
    second = _client(monkeypatch, db_path)
    first_profile = first.put(
        "/social/profile",
        json={
            "username": "first_builder",
            "display_name": "First Builder",
            "bio": "Builds source-grounded developer tools.",
        },
    ).json()
    second_profile = second.put(
        "/social/profile",
        json={"username": "second_builder", "bio": "Open source."},
    ).json()

    assert first.get("/social/profiles?q=second").json()[0]["username"] == "second_builder"
    assert first.get("/social/profiles/second_builder").json()["is_following"] is False
    post = second.post(
        "/social/posts", json={"body": "Sharing this engineering lesson by choice."}
    )
    assert post.status_code == 201
    assert first.get("/social/feed").json() == []
    assert first.post("/social/follow/second_builder").json()["created"] is True
    assert first.post("/social/follow/second_builder").json()["created"] is False
    feed = first.get("/social/feed").json()
    assert len(feed) == 1
    assert feed[0]["body"] == "Sharing this engineering lesson by choice."
    assert feed[0]["author"]["username"] == second_profile["username"]
    assert first.get("/social/profiles/second_builder").json()["follower_count"] == 1
    assert first.delete(f"/social/posts/{post.json()['post_id']}").status_code == 404
    assert second.delete(f"/social/posts/{post.json()['post_id']}").status_code == 204
    assert first.delete("/social/follow/second_builder").json()["removed"] is True
    assert first.get("/social/feed").json() == []
    assert first_profile["username"] == "first_builder"


def test_demo_seed_is_opt_in_idempotent_and_visible_in_discover_and_marketplace(
    tmp_path, monkeypatch
):
    client = _client(monkeypatch, str(tmp_path / "demo.db"))
    demo_settings = replace(default_settings, demo_seed_enabled=False)
    monkeypatch.setattr(feature_routes, "settings", demo_settings)

    assert client.get("/demo/status").json() == {"enabled": False}
    assert client.post("/demo/seed").status_code == 404

    monkeypatch.setattr(
        feature_routes, "settings", replace(demo_settings, demo_seed_enabled=True)
    )
    first_seed = client.post("/demo/seed")
    assert first_seed.status_code == 200
    assert first_seed.json() == {
        "creators": 6,
        "posts": 12,
        "listings": 13,
    }

    current_user_id = client.get("/auth/me").json()["user_id"]
    creators = client.get("/social/profiles").json()
    assert len(creators) == 6
    assert all(creator["is_demo"] for creator in creators)
    assert all(creator["user_id"] != current_user_id for creator in creators)
    assert client.post(
        "/auth/login",
        json={
            "email": "demo_sana@example.invalid",
            "password": "not-a-real-password",
        },
    ).status_code == 401

    discover_feed = client.get("/social/discover").json()
    assert len(discover_feed) == 12
    assert all(post["author"]["is_demo"] for post in discover_feed)
    assert all(post["author"]["user_id"] != current_user_id for post in discover_feed)
    assert client.get("/social/feed").json() == []

    listings = client.get("/marketplace/listings").json()
    assert {listing["product_type"] for listing in listings} == {
        "plugin",
        "library",
        "agent",
    }
    assert all(listing["seller"]["is_demo"] for listing in listings)
    assert client.get("/tips/received").json() == []

    _link_wallet(client, Account.create())
    sample_listing = listings[0]
    purchase = client.post(
        f"/marketplace/listings/{sample_listing['listing_id']}/purchase"
    )
    assert purchase.status_code == 409
    assert "preview-only" in purchase.json()["detail"]

    second_seed = client.post("/demo/seed")
    assert second_seed.status_code == 200
    assert second_seed.json() == {
        "creators": 0,
        "posts": 0,
        "listings": 0,
    }


def test_wallet_signature_verification_and_single_use(tmp_path, monkeypatch):
    client = _client(monkeypatch, str(tmp_path / "wallet.db"))
    wallet = Account.create()
    challenge = client.post(
        "/wallet/challenge", json={"address": wallet.address}
    ).json()
    bad_signature = Account.sign_message(
        encode_defunct(text="not the challenge"), private_key=wallet.key
    ).signature.hex()
    assert client.post(
        "/wallet/verify",
        json={
            "challenge_id": challenge["challenge_id"],
            "signature": bad_signature,
        },
    ).status_code == 409

    signature = Account.sign_message(
        encode_defunct(text=challenge["message"]), private_key=wallet.key
    ).signature.hex()
    verified = client.post(
        "/wallet/verify",
        json={"challenge_id": challenge["challenge_id"], "signature": signature},
    )
    assert verified.status_code == 200
    assert verified.json()["wallet_address"] == wallet.address
    assert client.get("/social/profile").json()["wallet_address"] == wallet.address
    assert client.post(
        "/wallet/verify",
        json={"challenge_id": challenge["challenge_id"], "signature": signature},
    ).status_code == 409


def test_sepolia_tip_preparation_receipt_verification_and_replay_protection(
    tmp_path, monkeypatch
):
    db_path = str(tmp_path / "tips.db")
    sender = _client(monkeypatch, db_path)
    recipient = _client(monkeypatch, db_path)
    sender_wallet = Account.create()
    recipient_wallet = Account.create()
    _link_wallet(sender, sender_wallet)
    recipient.put(
        "/social/profile", json={"username": "tip_recipient"}
    )
    _link_wallet(recipient, recipient_wallet)

    rpc_settings = replace(
        default_settings,
        db_path=db_path,
        sepolia_rpc_url="https://sepolia-rpc.example.test",
        sepolia_min_confirmations=2,
        tip_intent_ttl_minutes=30,
        tip_max_wei=10**18,
    )
    monkeypatch.setattr(tipping, "settings", rpc_settings)
    amount_wei = int(Decimal("0.01") * tipping.WEI_PER_ETH)
    tx_hash = "0x" + "ab" * 32
    rpc_results = {
        "eth_chainId": "0xaa36a7",
        "eth_getTransactionByHash": {
            "from": sender_wallet.address,
            "to": recipient_wallet.address,
            "value": hex(amount_wei),
            "chainId": "0xaa36a7",
            "blockNumber": "0x64",
        },
        "eth_getTransactionReceipt": {"status": "0x1", "blockNumber": "0x64"},
        "eth_blockNumber": "0x65",
    }

    class FakeResponse:
        def __init__(self, result):
            self.result = result

        def raise_for_status(self):
            pass

        def json(self):
            return {"jsonrpc": "2.0", "id": 1, "result": self.result}

    monkeypatch.setattr(
        tipping.httpx,
        "post",
        lambda url, json, timeout: FakeResponse(rpc_results[json["method"]]),
    )

    prepared = sender.post(
        "/tips/prepare",
        json={"recipient_username": "tip_recipient", "amount_eth": "0.01"},
    )
    assert prepared.status_code == 201
    assert prepared.json()["chain_id"] == tipping.SEPOLIA_CHAIN_ID
    assert prepared.json()["to"] == recipient_wallet.address
    assert prepared.json()["value"] == hex(amount_wei)
    intent = prepared.json()

    verified = sender.post(
        f"/tips/{intent['intent_id']}/verify", json={"tx_hash": tx_hash}
    )
    assert verified.status_code == 200
    assert verified.json()["status"] == "verified"
    assert verified.json()["confirmations"] == 2
    assert sender.post(
        f"/tips/{intent['intent_id']}/verify", json={"tx_hash": tx_hash}
    ).json()["tip_id"] == verified.json()["tip_id"]
    assert recipient.get("/tips/received").json()[0]["tx_hash"] == tx_hash

    second_intent = sender.post(
        "/tips/prepare",
        json={"recipient_username": "tip_recipient", "amount_eth": "0.01"},
    ).json()
    duplicate = sender.post(
        f"/tips/{second_intent['intent_id']}/verify", json={"tx_hash": tx_hash}
    )
    assert duplicate.status_code == 409
    assert "already been recorded" in duplicate.json()["detail"]


def test_tip_rejects_unconfirmed_mismatched_and_excessive_values(tmp_path, monkeypatch):
    db_path = str(tmp_path / "tip-reject.db")
    sender = _client(monkeypatch, db_path)
    recipient = _client(monkeypatch, db_path)
    sender_wallet = Account.create()
    recipient_wallet = Account.create()
    _link_wallet(sender, sender_wallet)
    recipient.put("/social/profile", json={"username": "unconfirmed_user"})
    _link_wallet(recipient, recipient_wallet)
    configured = replace(
        default_settings,
        db_path=db_path,
        sepolia_rpc_url="https://sepolia-rpc.example.test",
        sepolia_min_confirmations=3,
        tip_max_wei=10**18,
    )
    monkeypatch.setattr(tipping, "settings", configured)
    excessive = sender.post(
        "/tips/prepare",
        json={"recipient_username": "unconfirmed_user", "amount_eth": "2"},
    )
    assert excessive.status_code == 409

    intent = sender.post(
        "/tips/prepare",
        json={"recipient_username": "unconfirmed_user", "amount_eth": "0.01"},
    ).json()
    amount_wei = int(Decimal("0.01") * tipping.WEI_PER_ETH)
    rpc_results = {
        "eth_chainId": "0xaa36a7",
        "eth_getTransactionByHash": {
            "from": sender_wallet.address,
            "to": recipient_wallet.address,
            "value": hex(amount_wei + 1),
            "chainId": "0xaa36a7",
            "blockNumber": "0x64",
        },
        "eth_getTransactionReceipt": {"status": "0x1", "blockNumber": "0x64"},
        "eth_blockNumber": "0x65",
    }

    class FakeResponse:
        def __init__(self, result):
            self.result = result

        def raise_for_status(self):
            pass

        def json(self):
            return {"result": self.result}

    monkeypatch.setattr(
        tipping.httpx,
        "post",
        lambda url, json, timeout: FakeResponse(rpc_results[json["method"]]),
    )
    mismatch = sender.post(
        f"/tips/{intent['intent_id']}/verify",
        json={"tx_hash": "0x" + "cd" * 32},
    )
    assert mismatch.status_code == 409
    assert "does not match" in mismatch.json()["detail"]

    rpc_results["eth_getTransactionByHash"]["value"] = hex(amount_wei)
    not_confirmed = sender.post(
        f"/tips/{intent['intent_id']}/verify",
        json={"tx_hash": "0x" + "ef" * 32},
    )
    assert not_confirmed.status_code == 409
    assert "not confirmed" in not_confirmed.json()["detail"]


def test_wallet_challenges_expire_and_wallet_is_unique(tmp_path, monkeypatch):
    db_path = str(tmp_path / "wallet-unique.db")
    first = _client(monkeypatch, db_path)
    second = _client(monkeypatch, db_path)
    wallet = Account.create()
    _link_wallet(first, wallet)
    challenge = second.post(
        "/wallet/challenge", json={"address": wallet.address}
    ).json()
    signature = Account.sign_message(
        encode_defunct(text=challenge["message"]), private_key=wallet.key
    ).signature.hex()
    response = second.post(
        "/wallet/verify",
        json={"challenge_id": challenge["challenge_id"], "signature": signature},
    )
    assert response.status_code == 409
    assert "already linked" in response.json()["detail"]


def test_marketplace_sale_requires_verified_payment_and_gates_delivery_url(
    tmp_path, monkeypatch
):
    db_path = str(tmp_path / "marketplace.db")
    seller = _client(monkeypatch, db_path)
    buyer = _client(monkeypatch, db_path)
    seller_wallet = Account.create()
    buyer_wallet = Account.create()
    seller.put("/social/profile", json={"username": "agent_maker"})
    _link_wallet(seller, seller_wallet)
    _link_wallet(buyer, buyer_wallet)

    configured = replace(
        default_settings,
        db_path=db_path,
        sepolia_rpc_url="https://sepolia-rpc.example.test",
        sepolia_min_confirmations=2,
        tip_intent_ttl_minutes=30,
    )
    monkeypatch.setattr(tipping, "settings", configured)
    monkeypatch.setattr(marketplace, "settings", configured)
    private_url = "https://downloads.example.test/private/agent.zip?token=secret"
    listing_response = seller.post(
        "/marketplace/listings",
        json={
            "product_type": "agent",
            "title": "Code review agent",
            "description": "A focused review workflow.",
            "price_eth": "0.025",
            "delivery_url": private_url,
        },
    )
    assert listing_response.status_code == 201
    listing = listing_response.json()
    listing_id = listing["listing_id"]
    assert "delivery_url" not in listing
    assert private_url not in str(buyer.get("/marketplace/listings").json())

    prepared_response = buyer.post(
        f"/marketplace/listings/{listing_id}/purchase"
    )
    assert prepared_response.status_code == 201
    prepared = prepared_response.json()
    assert prepared["to"] == seller_wallet.address
    assert prepared["from"] == buyer_wallet.address
    assert prepared["value"] == hex(int(Decimal("0.025") * tipping.WEI_PER_ETH))
    assert buyer.get("/marketplace/purchases").json() == []

    tx_hash = "0x" + "cd" * 32
    rpc_results = {
        "eth_chainId": "0xaa36a7",
        "eth_getTransactionByHash": {
            "from": buyer_wallet.address,
            "to": seller_wallet.address,
            "value": prepared["value"],
            "chainId": "0xaa36a7",
            "blockNumber": "0x64",
        },
        "eth_getTransactionReceipt": {"status": "0x1", "blockNumber": "0x64"},
        "eth_blockNumber": "0x65",
    }

    class FakeResponse:
        def __init__(self, result):
            self.result = result

        def raise_for_status(self):
            pass

        def json(self):
            return {"result": self.result}

    monkeypatch.setattr(
        tipping.httpx,
        "post",
        lambda url, json, timeout: FakeResponse(rpc_results[json["method"]]),
    )
    verified = buyer.post(
        f"/marketplace/purchases/{prepared['intent_id']}/verify",
        json={"tx_hash": tx_hash},
    )
    assert verified.status_code == 200
    repeated = buyer.post(
        f"/marketplace/purchases/{prepared['intent_id']}/verify",
        json={"tx_hash": tx_hash},
    )
    assert repeated.status_code == 200
    assert repeated.json()["sale_id"] == verified.json()["sale_id"]
    purchase = buyer.get(f"/marketplace/purchases/{verified.json()['sale_id']}")
    assert purchase.status_code == 200
    assert purchase.json()["delivery_url"] == private_url
    assert seller.get(f"/marketplace/purchases/{verified.json()['sale_id']}").status_code == 404
    replayed_as_tip = buyer.post(
        "/tips/prepare",
        json={"recipient_username": "agent_maker", "amount_eth": "0.025"},
    )
    assert replayed_as_tip.status_code == 201
    duplicate_claim = buyer.post(
        f"/tips/{replayed_as_tip.json()['intent_id']}/verify",
        json={"tx_hash": tx_hash},
    )
    assert duplicate_claim.status_code == 409
    assert "already been recorded as a purchase" in duplicate_claim.json()["detail"]
    assert seller.delete(f"/marketplace/listings/{listing_id}").status_code == 204
    assert buyer.get(f"/marketplace/purchases/{verified.json()['sale_id']}").status_code == 200
