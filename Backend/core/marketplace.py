"""Creator listings and buyer-gated Sepolia purchases."""
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
import re
import sqlite3
import uuid
from urllib.parse import urlsplit

from config import settings
from core import storage, tipping

WEI_PER_ETH = tipping.WEI_PER_ETH
PRODUCT_TYPES = {"plugin", "library", "agent"}
_ID = re.compile(r"^[0-9a-f]{32}$")


class MarketplaceError(ValueError):
    pass


def _now() -> datetime:
    return tipping._now()


def _price_wei(amount_eth: str) -> int:
    try:
        amount = Decimal(amount_eth)
    except (InvalidOperation, ValueError) as exc:
        raise MarketplaceError("Price must be a valid ETH decimal.") from exc
    if not amount.is_finite() or amount <= 0:
        raise MarketplaceError("Price must be greater than zero.")
    wei = amount * WEI_PER_ETH
    if wei != wei.to_integral_value():
        raise MarketplaceError("Price may have at most 18 decimal places.")
    return int(wei)


def _validate_delivery_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.hostname.lower() in {"localhost", "127.0.0.1", "::1"}
    ):
        raise MarketplaceError("Delivery links must be HTTPS URLs without embedded credentials.")
    return value.strip()


def _public_listing(row) -> dict:
    return {
        "listing_id": row["listing_id"],
        "product_type": row["product_type"],
        "title": row["title"],
        "description": row["description"],
        "price_wei": row["price_wei"],
        "price_eth": str(Decimal(row["price_wei"]) / WEI_PER_ETH),
        "seller": {
            "username": row["username"],
            "display_name": row["display_name"],
            "is_demo": bool(row["is_demo"]),
        },
        "created_at": row["created_at"],
        "active": bool(row["active"]),
    }


def create_listing(
    seller_user_id: str,
    product_type: str,
    title: str,
    description: str,
    price_eth: str,
    delivery_url: str,
) -> dict:
    if product_type not in PRODUCT_TYPES:
        raise MarketplaceError("Product type must be plugin, library, or agent.")
    clean_title = title.strip()
    clean_description = description.strip()
    if not clean_title or len(clean_title) > 100:
        raise MarketplaceError("Title must contain 1 to 100 characters.")
    if not clean_description or len(clean_description) > 2000:
        raise MarketplaceError("Description must contain 1 to 2000 characters.")
    amount_wei = _price_wei(price_eth)
    clean_url = _validate_delivery_url(delivery_url)
    now = _now().isoformat()
    listing_id = uuid.uuid4().hex
    with storage.conn() as connection:
        seller = connection.execute(
            """SELECT wallet_address,wallet_verified_at FROM users
            WHERE user_id=? AND verified_at IS NOT NULL""",
            (seller_user_id,),
        ).fetchone()
        if seller is None:
            raise KeyError("Verified seller account not found.")
        if not seller["wallet_address"] or not seller["wallet_verified_at"]:
            raise MarketplaceError("Verify your wallet before listing a product.")
        connection.execute(
            """INSERT INTO marketplace_listings
            (listing_id,seller_user_id,product_type,title,description,price_wei,
            delivery_url,created_at,updated_at,active)
            VALUES(?,?,?,?,?,?,?,?,?,1)""",
            (
                listing_id, seller_user_id, product_type, clean_title,
                clean_description, str(amount_wei), clean_url, now, now,
            ),
        )
    result = get_listing(listing_id)
    if result is None:
        raise RuntimeError("New marketplace listing could not be loaded.")
    return result


def list_listings(
    query: str | None = None,
    product_type: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    if not 1 <= limit <= 50 or offset < 0:
        raise MarketplaceError("Marketplace pagination requires limit 1-50 and offset >= 0.")
    if product_type is not None and product_type not in PRODUCT_TYPES:
        raise MarketplaceError("Unknown marketplace product type.")
    sql = """SELECT l.listing_id,l.product_type,l.title,l.description,l.price_wei,
    l.created_at,l.active,u.username,u.display_name,u.is_demo
    FROM marketplace_listings l JOIN users u ON u.user_id=l.seller_user_id
    WHERE l.active=1 AND u.verified_at IS NOT NULL"""
    params: list[str | int] = []
    if product_type:
        sql += " AND l.product_type=?"
        params.append(product_type)
    if query and query.strip():
        needle = f"%{query.strip()}%"
        sql += " AND (l.title LIKE ? OR l.description LIKE ? OR u.username LIKE ?)"
        params.extend((needle, needle, needle))
    sql += " ORDER BY l.created_at DESC,l.listing_id LIMIT ? OFFSET ?"
    params.extend((limit, offset))
    with storage.conn() as connection:
        rows = connection.execute(sql, params).fetchall()
    return [_public_listing(row) for row in rows]


def get_listing(listing_id: str) -> dict | None:
    if not _ID.fullmatch(listing_id):
        return None
    with storage.conn() as connection:
        row = connection.execute(
            """SELECT l.listing_id,l.product_type,l.title,l.description,l.price_wei,
            l.created_at,l.active,u.username,u.display_name,u.is_demo
            FROM marketplace_listings l JOIN users u ON u.user_id=l.seller_user_id
            WHERE l.listing_id=? AND l.active=1 AND u.verified_at IS NOT NULL""",
            (listing_id,),
        ).fetchone()
    return _public_listing(row) if row else None


def list_my_listings(user_id: str) -> list[dict]:
    with storage.conn() as connection:
        rows = connection.execute(
            """SELECT l.listing_id,l.product_type,l.title,l.description,l.price_wei,
            l.created_at,l.active,u.username,u.display_name,u.is_demo
            FROM marketplace_listings l JOIN users u ON u.user_id=l.seller_user_id
            WHERE l.seller_user_id=? ORDER BY l.created_at DESC""",
            (user_id,),
        ).fetchall()
    return [_public_listing(row) for row in rows]


def deactivate_listing(seller_user_id: str, listing_id: str) -> bool:
    if not _ID.fullmatch(listing_id):
        return False
    with storage.conn() as connection:
        result = connection.execute(
            """UPDATE marketplace_listings SET active=0,updated_at=?
            WHERE listing_id=? AND seller_user_id=? AND active=1""",
            (_now().isoformat(), listing_id, seller_user_id),
        )
        return result.rowcount == 1


def prepare_purchase(buyer_user_id: str, listing_id: str) -> dict:
    if not _ID.fullmatch(listing_id):
        raise KeyError("Marketplace listing not found.")
    now = _now()
    if settings.tip_intent_ttl_minutes <= 0:
        raise MarketplaceError("TIP_INTENT_TTL_MINUTES must be greater than zero.")
    with storage.conn() as connection:
        buyer = connection.execute(
            """SELECT wallet_address,wallet_verified_at FROM users
            WHERE user_id=? AND verified_at IS NOT NULL""",
            (buyer_user_id,),
        ).fetchone()
        listing = connection.execute(
            """SELECT l.seller_user_id,l.price_wei,u.wallet_address,
            u.wallet_verified_at,u.is_demo FROM marketplace_listings l
            JOIN users u ON u.user_id=l.seller_user_id
            WHERE l.listing_id=? AND l.active=1 AND u.verified_at IS NOT NULL""",
            (listing_id,),
        ).fetchone()
        if buyer is None:
            raise KeyError("Verified buyer account not found.")
        if not buyer["wallet_address"] or not buyer["wallet_verified_at"]:
            raise MarketplaceError("Verify your wallet before purchasing.")
        if listing is None:
            raise KeyError("Marketplace listing not found.")
        if listing["is_demo"]:
            raise MarketplaceError("Sample listings are preview-only and cannot be purchased.")
        if listing["seller_user_id"] == buyer_user_id:
            raise MarketplaceError("You cannot purchase your own listing.")
        if not listing["wallet_address"] or not listing["wallet_verified_at"]:
            raise MarketplaceError("Seller wallet is not verified.")
        if buyer["wallet_address"].lower() == listing["wallet_address"].lower():
            raise MarketplaceError("Buyer and seller wallets must be different.")
        intent_id = uuid.uuid4().hex
        expires_at = now + timedelta(minutes=settings.tip_intent_ttl_minutes)
        connection.execute(
            """INSERT INTO marketplace_purchase_intents
            (intent_id,listing_id,buyer_user_id,seller_user_id,chain_id,from_address,
            to_address,amount_wei,created_at,expires_at,verified_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,NULL)""",
            (
                intent_id, listing_id, buyer_user_id, listing["seller_user_id"],
                tipping.SEPOLIA_CHAIN_ID, buyer["wallet_address"],
                listing["wallet_address"], listing["price_wei"], now.isoformat(),
                expires_at.isoformat(),
            ),
        )
    amount_wei = int(listing["price_wei"])
    return {
        "intent_id": intent_id,
        "listing_id": listing_id,
        "chain_id": tipping.SEPOLIA_CHAIN_ID,
        "from": buyer["wallet_address"],
        "to": listing["wallet_address"],
        "value": hex(amount_wei),
        "amount_wei": str(amount_wei),
        "expires_at": expires_at.isoformat(),
        "network": "Sepolia",
        "asset": "ETH",
    }


def _sale_response(row) -> dict:
    return {
        "sale_id": row["sale_id"],
        "listing_id": row["listing_id"],
        "title": row["title"],
        "product_type": row["product_type"],
        "amount_wei": row["amount_wei"],
        "tx_hash": row["tx_hash"],
        "verified_at": row["verified_at"],
        "status": "verified",
    }


def verify_purchase(buyer_user_id: str, intent_id: str, tx_hash: str) -> dict:
    if not tipping._TX_HASH.fullmatch(tx_hash):
        raise MarketplaceError("Transaction hash must be a 32-byte 0x-prefixed hex value.")
    if not _ID.fullmatch(intent_id):
        raise KeyError("Purchase intent not found.")
    if settings.sepolia_min_confirmations < 1:
        raise MarketplaceError("SEPOLIA_MIN_CONFIRMATIONS must be at least one.")
    with storage.conn() as connection:
        intent = connection.execute(
            """SELECT i.*,s.sale_id,s.tx_hash AS tx_hash,
            s.block_number,l.title,l.product_type
            FROM marketplace_purchase_intents i
            JOIN marketplace_listings l ON l.listing_id=i.listing_id
            LEFT JOIN marketplace_sales s ON s.intent_id=i.intent_id
            WHERE i.intent_id=? AND i.buyer_user_id=?""",
            (intent_id, buyer_user_id),
        ).fetchone()
    if intent is None:
        raise KeyError("Purchase intent not found.")
    if intent["verified_at"] is not None:
        if intent["tx_hash"] == tx_hash.lower():
            return _sale_response(intent)
        raise MarketplaceError("Purchase intent has already been verified.")
    if datetime.fromisoformat(intent["expires_at"]) <= _now():
        raise MarketplaceError("Purchase intent has expired.")

    chain_id = tipping._rpc("eth_chainId", [])
    if not isinstance(chain_id, str) or not tipping._HEX_QUANTITY.fullmatch(chain_id):
        raise MarketplaceError("Sepolia RPC returned an invalid chain ID.")
    if int(chain_id, 16) != tipping.SEPOLIA_CHAIN_ID or intent["chain_id"] != tipping.SEPOLIA_CHAIN_ID:
        raise MarketplaceError("Configured RPC is not the Sepolia network.")
    tx = tipping._rpc("eth_getTransactionByHash", [tx_hash])
    receipt = tipping._rpc("eth_getTransactionReceipt", [tx_hash])
    if not isinstance(tx, dict) or not isinstance(receipt, dict):
        raise MarketplaceError("Transaction is not yet available on Sepolia.")
    if (
        not isinstance(tx.get("from"), str)
        or tx["from"].lower() != intent["from_address"].lower()
        or not isinstance(tx.get("to"), str)
        or tx["to"].lower() != intent["to_address"].lower()
        or not isinstance(tx.get("value"), str)
        or not tipping._HEX_QUANTITY.fullmatch(tx["value"])
        or int(tx["value"], 16) != int(intent["amount_wei"])
        or not isinstance(tx.get("chainId"), str)
        or not tipping._HEX_QUANTITY.fullmatch(tx["chainId"])
        or int(tx["chainId"], 16) != tipping.SEPOLIA_CHAIN_ID
    ):
        raise MarketplaceError("On-chain transaction does not match the prepared purchase.")
    if receipt.get("status") != "0x1":
        raise MarketplaceError("Purchase transaction has not succeeded.")
    block_number = receipt.get("blockNumber")
    if not isinstance(block_number, str) or not tipping._HEX_QUANTITY.fullmatch(block_number):
        raise MarketplaceError("Sepolia RPC returned an invalid transaction receipt.")
    if tx.get("blockNumber") != block_number:
        raise MarketplaceError("Transaction and receipt block details do not match.")
    head = tipping._rpc("eth_blockNumber", [])
    if not isinstance(head, str) or not tipping._HEX_QUANTITY.fullmatch(head):
        raise MarketplaceError("Sepolia RPC returned an invalid latest block.")
    confirmations = int(head, 16) - int(block_number, 16) + 1
    if confirmations < settings.sepolia_min_confirmations:
        raise MarketplaceError(
            f"Purchase is not confirmed yet ({confirmations}/"
            f"{settings.sepolia_min_confirmations} confirmations)."
        )

    now = _now().isoformat()
    sale_id = uuid.uuid4().hex
    normalized_hash = tx_hash.lower()
    try:
        with storage.conn() as connection:
            connection.execute("BEGIN IMMEDIATE")
            latest = connection.execute(
                """SELECT verified_at,expires_at FROM marketplace_purchase_intents
                WHERE intent_id=? AND buyer_user_id=?""",
                (intent_id, buyer_user_id),
            ).fetchone()
            if (
                latest is None
                or latest["verified_at"] is not None
                or datetime.fromisoformat(latest["expires_at"]) <= _now()
            ):
                raise MarketplaceError("Purchase intent is expired or already verified.")
            reused = connection.execute(
                """SELECT 1 FROM verified_tips WHERE tx_hash=?
                UNION ALL SELECT 1 FROM marketplace_sales WHERE tx_hash=? LIMIT 1""",
                (normalized_hash, normalized_hash),
            ).fetchone()
            if reused:
                raise MarketplaceError("This transaction has already been claimed.")
            connection.execute(
                "UPDATE marketplace_purchase_intents SET verified_at=? WHERE intent_id=?",
                (now, intent_id),
            )
            connection.execute(
                """INSERT INTO marketplace_sales
                (sale_id,intent_id,tx_hash,listing_id,buyer_user_id,seller_user_id,
                chain_id,from_address,to_address,amount_wei,block_number,verified_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    sale_id, intent_id, normalized_hash, intent["listing_id"],
                    buyer_user_id, intent["seller_user_id"], intent["chain_id"],
                    intent["from_address"], intent["to_address"], intent["amount_wei"],
                    int(block_number, 16), now,
                ),
            )
    except sqlite3.IntegrityError as exc:
        raise MarketplaceError("This transaction has already been claimed.") from exc
    return {
        "sale_id": sale_id,
        "listing_id": intent["listing_id"],
        "title": intent["title"],
        "product_type": intent["product_type"],
        "amount_wei": intent["amount_wei"],
        "tx_hash": normalized_hash,
        "verified_at": now,
        "status": "verified",
    }


def list_my_purchases(buyer_user_id: str) -> list[dict]:
    with storage.conn() as connection:
        rows = connection.execute(
            """SELECT s.sale_id,s.listing_id,s.amount_wei,s.tx_hash,s.verified_at,
            l.title,l.product_type
            FROM marketplace_sales s JOIN marketplace_listings l
            ON l.listing_id=s.listing_id
            WHERE s.buyer_user_id=? ORDER BY s.verified_at DESC""",
            (buyer_user_id,),
        ).fetchall()
    return [_sale_response(row) for row in rows]


def get_purchase(buyer_user_id: str, sale_id: str) -> dict | None:
    if not _ID.fullmatch(sale_id):
        return None
    with storage.conn() as connection:
        row = connection.execute(
            """SELECT s.sale_id,s.listing_id,s.amount_wei,s.tx_hash,s.verified_at,
            l.title,l.product_type,l.delivery_url
            FROM marketplace_sales s JOIN marketplace_listings l
            ON l.listing_id=s.listing_id
            WHERE s.sale_id=? AND s.buyer_user_id=?""",
            (sale_id, buyer_user_id),
        ).fetchone()
    if row is None:
        return None
    result = _sale_response(row)
    result["delivery_url"] = row["delivery_url"]
    return result
