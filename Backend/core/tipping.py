"""Wallet proof, Sepolia transaction preparation, and receipt verification."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import re
import sqlite3
import uuid
from urllib.parse import urlsplit

import httpx
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import is_address, to_checksum_address

from config import settings
from core import notifications, storage

SEPOLIA_CHAIN_ID = 11155111
WEI_PER_ETH = 10**18
_TX_HASH = re.compile(r"^0x[0-9a-fA-F]{64}$")
_HEX_QUANTITY = re.compile(r"^0x(?:0|[1-9a-fA-F][0-9a-fA-F]*)$")


MAX_TIP_MESSAGE_CHARS = 140


class TipError(ValueError):
    pass


class TipRPCError(TipError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _rpc_url() -> str:
    url = urlsplit(settings.sepolia_rpc_url)
    if (
        not url.netloc
        or url.scheme not in {"http", "https"}
        or (
            url.scheme != "https"
            and url.hostname not in {"localhost", "127.0.0.1", "::1"}
        )
    ):
        raise TipRPCError(
            "Configure SEPOLIA_RPC_URL as HTTPS (or local HTTP for development)."
        )
    return settings.sepolia_rpc_url


def _rpc(method: str, params: list) -> object:
    try:
        response = httpx.post(
            _rpc_url(),
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise TipRPCError("Sepolia RPC request failed.") from exc
    if not isinstance(data, dict):
        raise TipRPCError("Sepolia RPC returned an invalid response.")
    if "error" in data:
        raise TipRPCError("Sepolia RPC rejected the verification request.")
    if "result" not in data:
        raise TipRPCError("Sepolia RPC response did not include a result.")
    return data["result"]


def start_wallet_challenge(user_id: str, wallet_address: str) -> dict:
    if not is_address(wallet_address):
        raise TipError("Enter a valid EVM wallet address.")
    address = to_checksum_address(wallet_address)
    now = _now()
    expires_at = now + timedelta(minutes=5)
    challenge_id = uuid.uuid4().hex
    with storage.conn() as connection:
        user = connection.execute(
            "SELECT username,verified_at FROM users WHERE user_id=?",
            (user_id,),
        ).fetchone()
        if user is None or user["verified_at"] is None:
            raise KeyError("Verified user not found.")
        nonce = uuid.uuid4().hex
        message = (
            "SocialPilot wallet verification\n"
            f"Account: @{user['username']}\n"
            f"Address: {address}\n"
            f"Nonce: {nonce}\n"
            f"Expires: {expires_at.isoformat()}\n"
            "Sign this message to prove you control this wallet. No transaction "
            "will be sent."
        )
        connection.execute(
            """UPDATE wallet_challenges SET used_at=?
            WHERE user_id=? AND used_at IS NULL""",
            (now.isoformat(), user_id),
        )
        connection.execute(
            """INSERT INTO wallet_challenges
            (challenge_id,user_id,wallet_address,message,created_at,expires_at,used_at)
            VALUES(?,?,?,?,?,?,NULL)""",
            (
                challenge_id,
                user_id,
                address,
                message,
                now.isoformat(),
                expires_at.isoformat(),
            ),
        )
    return {
        "challenge_id": challenge_id,
        "message": message,
        "expires_at": expires_at.isoformat(),
    }


def verify_wallet_challenge(user_id: str, challenge_id: str, signature: str) -> dict:
    with storage.conn() as connection:
        challenge = connection.execute(
            """SELECT wallet_address,message,expires_at,used_at
            FROM wallet_challenges WHERE challenge_id=? AND user_id=?""",
            (challenge_id, user_id),
        ).fetchone()
    if challenge is None or challenge["used_at"] is not None:
        raise TipError("Wallet challenge is invalid or already used.")
    if datetime.fromisoformat(challenge["expires_at"]) <= _now():
        raise TipError("Wallet challenge has expired.")
    try:
        recovered = Account.recover_message(
            encode_defunct(text=challenge["message"]), signature=signature
        )
    except (ValueError, TypeError) as exc:
        raise TipError("Wallet signature is invalid.") from exc
    if recovered.lower() != challenge["wallet_address"].lower():
        raise TipError("Signature does not match the challenged wallet.")

    now = _now().isoformat()
    with storage.conn() as connection:
        connection.execute("BEGIN IMMEDIATE")
        current = connection.execute(
            """SELECT wallet_address,used_at,expires_at FROM wallet_challenges
            WHERE challenge_id=? AND user_id=?""",
            (challenge_id, user_id),
        ).fetchone()
        if (
            current is None
            or current["used_at"] is not None
            or datetime.fromisoformat(current["expires_at"]) <= _now()
        ):
            raise TipError("Wallet challenge is invalid, expired, or already used.")
        try:
            connection.execute(
                """UPDATE users SET wallet_address=?,wallet_verified_at=?,updated_at=?
                WHERE user_id=?""",
                (current["wallet_address"], now, now, user_id),
            )
        except sqlite3.IntegrityError as exc:
            raise TipError(
                "This wallet is already linked to another account."
            ) from exc
        connection.execute(
            "UPDATE wallet_challenges SET used_at=? WHERE challenge_id=?",
            (now, challenge_id),
        )
    return {"wallet_address": challenge["wallet_address"], "verified": True}


def prepare_tip(
    sender_user_id: str,
    recipient_username: str | None,
    amount_eth: str,
    post_id: str | None = None,
    message: str | None = None,
) -> dict:
    message = (message or "").strip()
    if len(message) > MAX_TIP_MESSAGE_CHARS:
        raise TipError(f"Tip message must be at most {MAX_TIP_MESSAGE_CHARS} characters.")
    if not post_id and not recipient_username:
        raise TipError("Provide a recipient_username or a post_id.")
    try:
        amount = Decimal(amount_eth)
    except (InvalidOperation, ValueError) as exc:
        raise TipError("Tip amount must be a valid ETH decimal.") from exc
    if not amount.is_finite() or amount <= 0:
        raise TipError("Tip amount must be greater than zero.")
    wei = amount * WEI_PER_ETH
    if wei != wei.to_integral_value():
        raise TipError("ETH amount may have at most 18 decimal places.")
    amount_wei = int(wei)
    if settings.tip_max_wei <= 0 or amount_wei > settings.tip_max_wei:
        raise TipError("Tip amount exceeds the configured testnet limit.")
    if settings.tip_intent_ttl_minutes <= 0:
        raise TipError("TIP_INTENT_TTL_MINUTES must be greater than zero.")
    now = _now()
    with storage.conn() as connection:
        if post_id:
            post = connection.execute(
                """SELECT u.username FROM social_posts p JOIN users u ON u.user_id=p.user_id
                WHERE p.post_id=?""",
                (post_id,),
            ).fetchone()
            if post is None:
                raise KeyError("Post not found.")
            if recipient_username and recipient_username.lower() != post["username"].lower():
                raise TipError("That post does not belong to the chosen recipient.")
            recipient_username = post["username"]
        sender = connection.execute(
            """SELECT wallet_address,wallet_verified_at FROM users
            WHERE user_id=? AND verified_at IS NOT NULL""",
            (sender_user_id,),
        ).fetchone()
        recipient = connection.execute(
            """SELECT user_id,username,wallet_address,wallet_verified_at
            FROM users WHERE username=? COLLATE NOCASE AND verified_at IS NOT NULL""",
            (recipient_username,),
        ).fetchone()
        if sender is None:
            raise KeyError("Verified sender account not found.")
        if recipient is None:
            raise KeyError("Recipient profile not found.")
        if recipient["user_id"] == sender_user_id:
            raise TipError("You cannot tip your own account.")
        if sender["wallet_verified_at"] is None or not sender["wallet_address"]:
            raise TipError("Verify your wallet before preparing a tip.")
        if recipient["wallet_verified_at"] is None or not recipient["wallet_address"]:
            raise TipError("Recipient has not linked a verified wallet.")
        if sender["wallet_address"].lower() == recipient["wallet_address"].lower():
            raise TipError("Sender and recipient wallets must be different.")
        intent_id = uuid.uuid4().hex
        expires_at = now + timedelta(minutes=settings.tip_intent_ttl_minutes)
        connection.execute(
            """INSERT INTO tip_intents
            (intent_id,sender_user_id,recipient_user_id,chain_id,from_address,
            to_address,amount_wei,created_at,expires_at,verified_at,post_id,message)
            VALUES(?,?,?,?,?,?,?,?,?,NULL,?,?)""",
            (
                intent_id,
                sender_user_id,
                recipient["user_id"],
                SEPOLIA_CHAIN_ID,
                sender["wallet_address"],
                recipient["wallet_address"],
                str(amount_wei),
                now.isoformat(),
                expires_at.isoformat(),
                post_id,
                message,
            ),
        )
    return {
        "post_id": post_id,
        "message": message,
        "intent_id": intent_id,
        "chain_id": SEPOLIA_CHAIN_ID,
        "from": sender["wallet_address"],
        "to": recipient["wallet_address"],
        "value": hex(amount_wei),
        "amount_wei": str(amount_wei),
        "expires_at": expires_at.isoformat(),
        "network": "Sepolia",
        "asset": "ETH",
    }


def verify_tip(sender_user_id: str, intent_id: str, tx_hash: str) -> dict:
    if not _TX_HASH.fullmatch(tx_hash):
        raise TipError("Transaction hash must be a 32-byte 0x-prefixed hex value.")
    if settings.sepolia_min_confirmations < 1:
        raise TipError("SEPOLIA_MIN_CONFIRMATIONS must be at least one.")
    with storage.conn() as connection:
        intent = connection.execute(
            """SELECT i.*,t.tip_id,t.tx_hash AS verified_tx_hash,t.block_number
            FROM tip_intents i LEFT JOIN verified_tips t ON t.intent_id=i.intent_id
            WHERE i.intent_id=? AND i.sender_user_id=?""",
            (intent_id, sender_user_id),
        ).fetchone()
    if intent is None:
        raise KeyError("Tip intent not found.")
    if intent["verified_at"] is not None:
        if intent["verified_tx_hash"] == tx_hash.lower():
            return _tip_response(intent)
        raise TipError("Tip intent has already been verified.")
    if datetime.fromisoformat(intent["expires_at"]) <= _now():
        raise TipError("Tip intent has expired.")

    chain_id = _rpc("eth_chainId", [])
    if not isinstance(chain_id, str) or not _HEX_QUANTITY.fullmatch(chain_id):
        raise TipError("Sepolia RPC returned an invalid chain ID.")
    if int(chain_id, 16) != SEPOLIA_CHAIN_ID or intent["chain_id"] != SEPOLIA_CHAIN_ID:
        raise TipError("Configured RPC is not the Sepolia network.")

    tx = _rpc("eth_getTransactionByHash", [tx_hash])
    receipt = _rpc("eth_getTransactionReceipt", [tx_hash])
    if not isinstance(tx, dict) or not isinstance(receipt, dict):
        raise TipError("Transaction is not yet available on Sepolia.")
    if (
        tx.get("from", "").lower() != intent["from_address"].lower()
        or tx.get("to", "").lower() != intent["to_address"].lower()
        or not isinstance(tx.get("value"), str)
        or not _HEX_QUANTITY.fullmatch(tx["value"])
        or int(tx["value"], 16) != int(intent["amount_wei"])
        or not isinstance(tx.get("chainId"), str)
        or not _HEX_QUANTITY.fullmatch(tx["chainId"])
        or int(tx["chainId"], 16) != SEPOLIA_CHAIN_ID
    ):
        raise TipError("On-chain transaction does not match the prepared tip.")
    if receipt.get("status") != "0x1":
        raise TipError("Tip transaction has not succeeded.")
    block_number = receipt.get("blockNumber")
    if not isinstance(block_number, str) or not _HEX_QUANTITY.fullmatch(block_number):
        raise TipError("Sepolia RPC returned an invalid transaction receipt.")
    if tx.get("blockNumber") != block_number:
        raise TipError("Transaction and receipt block details do not match.")
    head = _rpc("eth_blockNumber", [])
    if not isinstance(head, str) or not _HEX_QUANTITY.fullmatch(head):
        raise TipError("Sepolia RPC returned an invalid latest block.")
    confirmations = int(head, 16) - int(block_number, 16) + 1
    if confirmations < settings.sepolia_min_confirmations:
        raise TipError(
            f"Tip is not confirmed yet ({confirmations}/"
            f"{settings.sepolia_min_confirmations} confirmations)."
        )

    now = _now().isoformat()
    tip_id = uuid.uuid4().hex
    normalized_hash = tx_hash.lower()
    try:
        with storage.conn() as connection:
            connection.execute("BEGIN IMMEDIATE")
            latest_intent = connection.execute(
                """SELECT verified_at,expires_at FROM tip_intents
                WHERE intent_id=? AND sender_user_id=?""",
                (intent_id, sender_user_id),
            ).fetchone()
            if (
                latest_intent is None
                or latest_intent["verified_at"] is not None
                or datetime.fromisoformat(latest_intent["expires_at"]) <= _now()
            ):
                raise TipError("Tip intent is expired or already verified.")
            already_claimed = connection.execute(
                "SELECT 1 FROM marketplace_sales WHERE tx_hash=?",
                (normalized_hash,),
            ).fetchone()
            if already_claimed:
                raise TipError("This transaction has already been recorded as a purchase.")
            connection.execute(
                "UPDATE tip_intents SET verified_at=? WHERE intent_id=?",
                (now, intent_id),
            )
            connection.execute(
                """INSERT INTO verified_tips
                (tip_id,intent_id,tx_hash,sender_user_id,recipient_user_id,chain_id,
                from_address,to_address,amount_wei,block_number,verified_at,
                post_id,message)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    tip_id,
                    intent_id,
                    normalized_hash,
                    sender_user_id,
                    intent["recipient_user_id"],
                    SEPOLIA_CHAIN_ID,
                    intent["from_address"],
                    intent["to_address"],
                    intent["amount_wei"],
                    int(block_number, 16),
                    now,
                    intent["post_id"],
                    intent["message"],
                ),
            )
            notifications.notify(
                connection,
                intent["recipient_user_id"],
                sender_user_id,
                "tip",
                intent["post_id"],
                tip_id,
            )
    except sqlite3.IntegrityError as exc:
        raise TipError("This transaction has already been recorded as a tip.") from exc
    return {
        "tip_id": tip_id,
        "intent_id": intent_id,
        "tx_hash": normalized_hash,
        "chain_id": SEPOLIA_CHAIN_ID,
        "network": "Sepolia",
        "asset": "ETH",
        "from": intent["from_address"],
        "to": intent["to_address"],
        "amount_wei": intent["amount_wei"],
        "block_number": int(block_number, 16),
        "confirmations": confirmations,
        "post_id": intent["post_id"],
        "message": intent["message"],
        "verified_at": now,
        "status": "verified",
    }


def _tip_response(row) -> dict:
    return {
        "tip_id": row["tip_id"],
        "intent_id": row["intent_id"],
        "tx_hash": row["verified_tx_hash"],
        "chain_id": row["chain_id"],
        "network": "Sepolia",
        "asset": "ETH",
        "from": row["from_address"],
        "to": row["to_address"],
        "amount_wei": row["amount_wei"],
        "block_number": row["block_number"],
        "post_id": row["post_id"],
        "message": row["message"],
        "verified_at": row["verified_at"],
        "status": "verified",
    }


def list_received_tips(user_id: str, limit: int = 20, offset: int = 0) -> list[dict]:
    if not 1 <= limit <= 50 or offset < 0:
        raise ValueError("Tip pagination requires limit 1-50 and offset >= 0.")
    with storage.conn() as connection:
        rows = connection.execute(
            """SELECT t.tip_id,t.intent_id,t.tx_hash AS verified_tx_hash,
            t.chain_id,t.from_address,
            t.to_address,t.amount_wei,t.block_number,t.verified_at,
            t.post_id,t.message,
            u.username AS sender_username
            FROM verified_tips t JOIN users u ON u.user_id=t.sender_user_id
            WHERE t.recipient_user_id=?
            ORDER BY t.verified_at DESC,t.tip_id DESC LIMIT ? OFFSET ?""",
            (user_id, limit, offset),
        ).fetchall()
    return [
        {
            **_tip_response(row),
            "sender_username": row["sender_username"],
        }
        for row in rows
    ]


def list_sent_tips(user_id: str, limit: int = 20, offset: int = 0) -> list[dict]:
    if not 1 <= limit <= 50 or offset < 0:
        raise ValueError("Tip pagination requires limit 1-50 and offset >= 0.")
    with storage.conn() as connection:
        rows = connection.execute(
            """SELECT t.tip_id,t.intent_id,t.tx_hash AS verified_tx_hash,t.chain_id,
            t.from_address,t.to_address,t.amount_wei,t.block_number,t.verified_at,
            t.post_id,t.message,u.username AS recipient_username
            FROM verified_tips t JOIN users u ON u.user_id=t.recipient_user_id
            WHERE t.sender_user_id=?
            ORDER BY t.verified_at DESC,t.tip_id DESC LIMIT ? OFFSET ?""",
            (user_id, limit, offset),
        ).fetchall()
    return [{**_tip_response(row), "recipient_username": row["recipient_username"]} for row in rows]


def list_post_tips(post_id: str, limit: int = 20, offset: int = 0) -> list[dict]:
    """Public supporters of a post (the transfers are public on-chain anyway)."""
    if not 1 <= limit <= 50 or offset < 0:
        raise ValueError("Tip pagination requires limit 1-50 and offset >= 0.")
    with storage.conn() as connection:
        if connection.execute(
            "SELECT 1 FROM social_posts WHERE post_id=?", (post_id,)
        ).fetchone() is None:
            raise KeyError("Post not found.")
        rows = connection.execute(
            """SELECT t.tip_id,t.amount_wei,t.message,t.verified_at,t.tx_hash,
            u.username AS sender_username,u.display_name AS sender_display_name
            FROM verified_tips t JOIN users u ON u.user_id=t.sender_user_id
            WHERE t.post_id=? ORDER BY t.verified_at DESC,t.tip_id DESC LIMIT ? OFFSET ?""",
            (post_id, limit, offset),
        ).fetchall()
    return [dict(row) for row in rows]
