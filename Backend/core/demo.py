"""Idempotent sample creators and marketplace items for opt-in demos."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

from core import storage

_NAMESPACE = uuid.UUID("92f8b31a-5501-4c7d-b9ca-c6d5d6930718")
_CREATORS = (
    {"username": "demo_sana", "display_name": "Sana Rios",
     "bio": "Building accessible design systems and React tooling."},
    {"username": "demo_mika", "display_name": "Mika Chen",
     "bio": "Open-source maintainer exploring reliable developer workflows."},
    {"username": "demo_leo", "display_name": "Leo Martin",
     "bio": "Small libraries, thoughtful docs, and practical AI agents."},
    {"username": "demo_priya", "display_name": "Priya Nair",
     "bio": "Platform engineer. Remote from Bengaluru, UTC+5:30. Observability and CI."},
    {"username": "demo_tomas", "display_name": "Tomas Novak",
     "bio": "Application security for small teams: secrets, dependencies, supply chain."},
    {"username": "demo_aiko", "display_name": "Aiko Tanaka",
     "bio": "Data and ML tooling. Writes about evaluating LLM features honestly."},
)
# (author, markdown body, tags, hours ago)
_POSTS = (
    ("demo_sana",
     "I built PaletteLint, a small VS Code extension that catches low-contrast color pairs while you work. The useful lesson: accessibility checks help most when they show up before review, not after it.",
     ("accessibility", "vscode"), 2),
    ("demo_mika",
     "This week I released QueueKit, a TypeScript library for retryable background jobs. I focused the first version on predictable backoff and readable failure states instead of adding every queue feature at once.",
     ("typescript", "queues"), 5),
    ("demo_leo",
     "I prototyped a docs assistant that cites the exact source section behind each answer. The best improvement came from making citations part of the output contract instead of a follow-up feature.",
     ("ai", "docs"), 9),
    ("demo_sana",
     "A tiny component API can still carry a lot of design-system value. I shared a set of keyboard-first React primitives today, with examples that show the focus states as well as the happy path.",
     ("react", "accessibility"), 14),
    ("demo_mika",
     "Maintainer note: our release checklist now runs against a clean install and a minimal example app. That caught a packaging issue our unit tests could not see.",
     ("opensource", "testing"), 20),
    ("demo_priya",
     "## TIL: SQLite WAL mode\n\nWith `PRAGMA journal_mode=WAL;` readers no longer block the writer, which was enough to remove most of our `database is locked` errors in CI.\n\n```sql\nPRAGMA journal_mode=WAL;\nPRAGMA synchronous=NORMAL;\n```\n\nStill single-writer, so we keep transactions short.",
     ("sqlite", "database", "til"), 26),
    ("demo_tomas",
     "Our pre-commit secret scan found a live API key in a *test fixture*. Lesson: scan fixtures and docs too, and rotate first, clean history second.\n\n- scan on every commit\n- block, don't just warn\n- rotate before rewriting git history",
     ("security", "git"), 31),
    ("demo_aiko",
     "Before shipping an LLM feature we now run a 40-example eval set on every prompt change. The first run showed our \"improved\" prompt was **worse on 9 cases**. Cheap evals beat gut feel.",
     ("llm", "evals"), 40),
    ("demo_priya",
     "Working across time zones: we moved standups to a written thread with a 24h window. Meetings dropped from 5 to 1 a week and decisions got written down by default.",
     ("remote", "teams"), 52),
    ("demo_leo",
     "Small library, big lesson: `retry(fn, { attempts: 3 })` looks harmless until `fn` is not idempotent. Document idempotency requirements next to the retry option, not in a separate guide.",
     ("api-design", "typescript"), 60),
    ("demo_tomas",
     "Supply-chain tip: pin GitHub Actions to a commit SHA, not a tag. Tags can move; SHAs can't.\n\n```yaml\n- uses: actions/checkout@<full-commit-sha>\n```",
     ("security", "ci"), 75),
    ("demo_aiko",
     "Open to collaboration: I'm looking for one or two people to help write a small benchmark for source-grounded summaries (do claims map back to the text?). Remote, async, weekends.",
     ("ai", "remote", "collab"), 90),
)
_LISTINGS = (
    # ---- plugins
    {"seller": "demo_sana", "product_type": "plugin", "title": "PaletteLint for VS Code", "price_eth": "0.01",
     "description": "Sample editor extension concept: flags low-contrast color pairs in CSS, Tailwind and JSX as you type and suggests the nearest accessible alternative. Works offline.",
     "delivery_url": "https://example.invalid/demo/palette-lint"},
    {"seller": "demo_tomas", "product_type": "plugin", "title": "EnvGuard Pre-commit", "price_eth": "0.008",
     "description": "Sample pre-commit hook concept that blocks commits containing API keys, private keys and .env files, including inside test fixtures and docs. Ships with a baseline file for known false positives.",
     "delivery_url": "https://example.invalid/demo/envguard"},
    {"seller": "demo_mika", "product_type": "plugin", "title": "CommitCraft for JetBrains", "price_eth": "0.012",
     "description": "Sample IDE plugin concept that drafts Conventional Commit messages from your staged diff. Local-only: nothing leaves your machine.",
     "delivery_url": "https://example.invalid/demo/commitcraft"},
    {"seller": "demo_priya", "product_type": "plugin", "title": "Standup Scribe for Slack", "price_eth": "0.006",
     "description": "Sample Slack app concept for distributed teams: collects written standups across time zones and posts one digest per region at the start of each local workday.",
     "delivery_url": "https://example.invalid/demo/standup-scribe"},
    # ---- libraries
    {"seller": "demo_mika", "product_type": "library", "title": "QueueKit TypeScript", "price_eth": "0.015",
     "description": "Sample typed job-queue library concept with retry policies, exponential backoff with jitter, and inspectable job states. Zero runtime dependencies.",
     "delivery_url": "https://example.invalid/demo/queuekit"},
    {"seller": "demo_priya", "product_type": "library", "title": "TinyTZ", "price_eth": "0.005",
     "description": "Sample Python library concept for remote teams: find meeting slots that fit everyone's working hours and render times in each teammate's local zone.",
     "delivery_url": "https://example.invalid/demo/tinytz"},
    {"seller": "demo_leo", "product_type": "library", "title": "RetryWise for Go", "price_eth": "0.009",
     "description": "Sample Go library concept: context-aware retries with budgeted attempts, jittered backoff and an idempotency-key helper.",
     "delivery_url": "https://example.invalid/demo/retrywise"},
    {"seller": "demo_aiko", "product_type": "library", "title": "FastPaginate", "price_eth": "0.011",
     "description": "Sample FastAPI library concept for cursor-based pagination: stable ordering, opaque cursors and typed response models for SQLAlchemy and SQLite.",
     "delivery_url": "https://example.invalid/demo/fastpaginate"},
    {"seller": "demo_sana", "product_type": "library", "title": "ReceiptKit (ethers.js)", "price_eth": "0.018",
     "description": "Sample helper library concept for verifying that an on-chain transfer really matches an expected sender, recipient and amount, with confirmation depth checks.",
     "delivery_url": "https://example.invalid/demo/receiptkit"},
    # ---- agents
    {"seller": "demo_leo", "product_type": "agent", "title": "Citedocs Assistant", "price_eth": "0.02",
     "description": "Sample documentation assistant concept that pairs every answer with the exact source section it came from, so you can verify before you trust.",
     "delivery_url": "https://example.invalid/demo/citedocs"},
    {"seller": "demo_tomas", "product_type": "agent", "title": "PR Reviewer Agent", "price_eth": "0.03",
     "description": "Sample code-review agent concept that comments on risky changes (auth, migrations, dependency bumps) and links each comment to the lines it refers to.",
     "delivery_url": "https://example.invalid/demo/pr-reviewer"},
    {"seller": "demo_priya", "product_type": "agent", "title": "Incident Notes Agent", "price_eth": "0.025",
     "description": "Sample on-call helper concept that turns a chat incident channel into a timeline and a blameless post-mortem draft, flagging gaps it could not source.",
     "delivery_url": "https://example.invalid/demo/incident-notes"},
    {"seller": "demo_aiko", "product_type": "agent", "title": "Changelog Writer Agent", "price_eth": "0.014",
     "description": "Sample release-notes agent concept that groups merged PRs into user-facing changes and links each line back to its pull request.",
     "delivery_url": "https://example.invalid/demo/changelog-writer"},
)
def _stable_id(kind: str, key: str) -> str:
    return uuid.uuid5(_NAMESPACE, f"{kind}:{key}").hex


def seed_demo_content() -> dict[str, int]:
    """Insert the sample catalog once; sample products are intentionally non-purchasable."""
    now = datetime.now(timezone.utc).isoformat()
    user_ids = {
        creator["username"]: _stable_id("user", creator["username"])
        for creator in _CREATORS
    }
    created = {"creators": 0, "posts": 0, "listings": 0}
    with storage.conn() as connection:
        for creator in _CREATORS:
            user_id = user_ids[creator["username"]]
            existing_rows = connection.execute(
                """SELECT user_id,username,email,is_demo FROM users
                WHERE username=? COLLATE NOCASE OR email=? COLLATE NOCASE
                    OR user_id=?""",
                (
                    creator["username"],
                    f"{creator['username']}@example.invalid",
                    user_id,
                ),
            ).fetchall()
            if existing_rows and any(
                row["user_id"] != user_id
                or row["username"] != creator["username"]
                or row["email"] != f"{creator['username']}@example.invalid"
                or not row["is_demo"]
                for row in existing_rows
            ):
                raise RuntimeError(
                    f"Cannot seed sample creator @{creator['username']}; its username or email is already in use."
                )
            if not existing_rows:
                connection.execute(
                    """INSERT INTO users(
                        user_id,email,display_name,password_hash,created_at,updated_at,
                        verified_at,username,bio,is_demo
                    ) VALUES(?,?,?,?,?,?,?,?,?,1)""",
                    (
                        user_id,
                        f"{creator['username']}@example.invalid",
                        creator["display_name"],
                        None,
                        now,
                        now,
                        now,
                        creator["username"],
                        creator["bio"],
                    ),
                )
                created["creators"] += 1

        for index, (username, body, tags, hours_ago) in enumerate(_POSTS):
            post_id = _stable_id("post", str(index))
            posted_at = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()
            cursor = connection.execute(
                """INSERT OR IGNORE INTO social_posts(post_id,user_id,body,created_at,format)
                VALUES(?,?,?,?,?)""",
                (post_id, user_ids[username], body, posted_at,
                 "markdown" if ("```" in body or "##" in body or "**" in body or "\n- " in body) else "plain"),
            )
            created["posts"] += cursor.rowcount
            connection.executemany(
                "INSERT OR IGNORE INTO post_tags(post_id,tag) VALUES(?,?)",
                [(post_id, tag) for tag in tags],
            )

        for listing in _LISTINGS:
            listing_id = _stable_id("listing", listing["title"])
            amount_wei = str(int(Decimal(listing["price_eth"]) * 10**18))
            cursor = connection.execute(
                """INSERT OR IGNORE INTO marketplace_listings(
                    listing_id,seller_user_id,product_type,title,description,price_wei,
                    delivery_url,created_at,updated_at,active
                ) VALUES(?,?,?,?,?,?,?,?,?,1)""",
                (
                    listing_id,
                    user_ids[listing["seller"]],
                    listing["product_type"],
                    listing["title"],
                    listing["description"],
                    amount_wei,
                    listing["delivery_url"],
                    now,
                    now,
                ),
            )
            created["listings"] += cursor.rowcount
    return created
