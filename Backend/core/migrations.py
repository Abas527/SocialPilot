"""Transactional, versioned SQLite schema migrations."""
import sqlite3
from datetime import datetime, timezone

Migration = tuple[int, str, tuple[str, ...]]

MIGRATIONS: tuple[Migration, ...] = (
    (
        1,
        "initial_project_storage",
        (
            """CREATE TABLE IF NOT EXISTS projects(
                project_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                repository_url TEXT,
                commit_sha TEXT,
                profile_json TEXT,
                created_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS source_documents(
                project_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                path TEXT NOT NULL,
                content TEXT NOT NULL,
                source_url TEXT,
                commit_sha TEXT,
                PRIMARY KEY(project_id, source_id)
            )""",
            """CREATE TABLE IF NOT EXISTS artifacts(
                artifact_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                artifact_type TEXT NOT NULL,
                generated_json TEXT NOT NULL,
                edited_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, artifact_type)
            )""",
            "CREATE INDEX IF NOT EXISTS idx_projects_created ON projects(created_at DESC)",
        ),
    ),
    (
        2,
        "persistent_rag_chunks",
        (
            """CREATE TABLE IF NOT EXISTS project_chunks(
                project_id TEXT NOT NULL,
                chunk_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                path TEXT NOT NULL,
                text TEXT NOT NULL,
                start_line INTEGER NOT NULL,
                end_line INTEGER NOT NULL,
                heading TEXT,
                source_url TEXT,
                PRIMARY KEY(project_id, chunk_id),
                FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE
            )""",
            """CREATE TABLE IF NOT EXISTS project_rag_index(
                project_id TEXT PRIMARY KEY,
                chunk_chars INTEGER NOT NULL CHECK(chunk_chars > 0),
                chunk_count INTEGER NOT NULL CHECK(chunk_count >= 0),
                indexed_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE
            )""",
            "CREATE INDEX IF NOT EXISTS idx_project_chunks_project ON project_chunks(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_project_chunks_path ON project_chunks(project_id,path,start_line)",
        ),
    ),
    (
        3,
        "users_sessions_and_project_ownership",
        (
            """CREATE TABLE IF NOT EXISTS users(
                user_id TEXT PRIMARY KEY,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                display_name TEXT NOT NULL,
                password_hash TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                CHECK(length(trim(email)) > 0),
                CHECK(length(trim(display_name)) > 0),
                CHECK(password_hash IS NULL OR length(password_hash) > 0)
            )""",
            """CREATE TABLE IF NOT EXISTS auth_sessions(
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                CHECK(expires_at > created_at),
                CHECK(length(token_hash) = 64),
                CHECK(token_hash NOT GLOB '*[^0-9a-f]*')
            )""",
            "CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_auth_sessions_expiry ON auth_sessions(expires_at)",
            """CREATE TABLE IF NOT EXISTS project_owners(
                project_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                assigned_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )""",
            "CREATE INDEX IF NOT EXISTS idx_project_owners_user ON project_owners(user_id)",
            """CREATE TABLE IF NOT EXISTS source_documents_new(
                project_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                path TEXT NOT NULL,
                content TEXT NOT NULL,
                source_url TEXT,
                commit_sha TEXT,
                PRIMARY KEY(project_id, source_id),
                FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE
            )""",
            """INSERT INTO source_documents_new
                (project_id,source_id,path,content,source_url,commit_sha)
                SELECT project_id,source_id,path,content,source_url,commit_sha
                FROM source_documents""",
            "DROP TABLE source_documents",
            "ALTER TABLE source_documents_new RENAME TO source_documents",
            """CREATE TABLE artifacts_new(
                artifact_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                artifact_type TEXT NOT NULL,
                generated_json TEXT NOT NULL,
                edited_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(project_id, artifact_type),
                FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE
            )""",
            """INSERT INTO artifacts_new
                (artifact_id,project_id,artifact_type,generated_json,edited_json,created_at,updated_at)
                SELECT artifact_id,project_id,artifact_type,generated_json,edited_json,created_at,updated_at
                FROM artifacts""",
            "DROP TABLE artifacts",
            "ALTER TABLE artifacts_new RENAME TO artifacts",
        ),
    ),
    (
        4,
        "email_verification",
        (
            "ALTER TABLE users ADD COLUMN verified_at TEXT",
            """CREATE TABLE email_verification_tokens(
                token_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                used_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                CHECK(expires_at > created_at),
                CHECK(length(token_hash) = 64),
                CHECK(token_hash NOT GLOB '*[^0-9a-f]*')
            )""",
            "CREATE INDEX idx_email_verification_user ON email_verification_tokens(user_id)",
            "CREATE INDEX idx_email_verification_expiry ON email_verification_tokens(expires_at)",
        ),
    ),
    (
        5,
        "social_profiles_follows_and_feed",
        (
            "ALTER TABLE users ADD COLUMN username TEXT",
            "ALTER TABLE users ADD COLUMN bio TEXT NOT NULL DEFAULT ''",
            """UPDATE users SET username='user_' || lower(substr(user_id,1,12))
            WHERE username IS NULL""",
            "CREATE UNIQUE INDEX idx_users_username ON users(username COLLATE NOCASE)",
            """CREATE TABLE follows(
                follower_user_id TEXT NOT NULL,
                followed_user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(follower_user_id,followed_user_id),
                FOREIGN KEY(follower_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY(followed_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                CHECK(follower_user_id != followed_user_id)
            )""",
            "CREATE INDEX idx_follows_followed ON follows(followed_user_id,follower_user_id)",
            """CREATE TABLE social_posts(
                post_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                CHECK(length(trim(body)) BETWEEN 1 AND 2000)
            )""",
            "CREATE INDEX idx_social_posts_feed ON social_posts(created_at DESC,post_id)",
            "CREATE INDEX idx_social_posts_user ON social_posts(user_id,created_at DESC)",
        ),
    ),
    (
        6,
        "verified_wallets_and_sepolia_tips",
        (
            "ALTER TABLE users ADD COLUMN wallet_address TEXT",
            "ALTER TABLE users ADD COLUMN wallet_verified_at TEXT",
            """CREATE UNIQUE INDEX idx_users_wallet_address
            ON users(wallet_address COLLATE NOCASE) WHERE wallet_address IS NOT NULL""",
            """CREATE TABLE wallet_challenges(
                challenge_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                wallet_address TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                used_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                CHECK(expires_at > created_at)
            )""",
            "CREATE INDEX idx_wallet_challenges_user ON wallet_challenges(user_id)",
            """CREATE TABLE tip_intents(
                intent_id TEXT PRIMARY KEY,
                sender_user_id TEXT NOT NULL,
                recipient_user_id TEXT NOT NULL,
                chain_id INTEGER NOT NULL,
                from_address TEXT NOT NULL,
                to_address TEXT NOT NULL,
                amount_wei TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                verified_at TEXT,
                FOREIGN KEY(sender_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY(recipient_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                CHECK(sender_user_id != recipient_user_id),
                CHECK(amount_wei NOT GLOB '*[^0-9]*'),
                CHECK(length(amount_wei) > 0),
                CHECK(expires_at > created_at)
            )""",
            "CREATE INDEX idx_tip_intents_sender ON tip_intents(sender_user_id,created_at DESC)",
            """CREATE TABLE verified_tips(
                tip_id TEXT PRIMARY KEY,
                intent_id TEXT NOT NULL UNIQUE,
                tx_hash TEXT NOT NULL UNIQUE,
                sender_user_id TEXT NOT NULL,
                recipient_user_id TEXT NOT NULL,
                chain_id INTEGER NOT NULL,
                from_address TEXT NOT NULL,
                to_address TEXT NOT NULL,
                amount_wei TEXT NOT NULL,
                block_number INTEGER NOT NULL,
                verified_at TEXT NOT NULL,
                FOREIGN KEY(intent_id) REFERENCES tip_intents(intent_id) ON DELETE CASCADE,
                FOREIGN KEY(sender_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY(recipient_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                CHECK(sender_user_id != recipient_user_id),
                CHECK(amount_wei NOT GLOB '*[^0-9]*'),
                CHECK(length(amount_wei) > 0),
                CHECK(block_number >= 0)
            )""",
            "CREATE INDEX idx_verified_tips_recipient ON verified_tips(recipient_user_id,verified_at DESC)",
        ),
    ),
    (
        7,
        "sepolia_creator_marketplace",
        (
            """CREATE TABLE marketplace_listings(
                listing_id TEXT PRIMARY KEY,
                seller_user_id TEXT NOT NULL,
                product_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                price_wei TEXT NOT NULL,
                delivery_url TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY(seller_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                CHECK(product_type IN ('plugin','library','agent')),
                CHECK(length(trim(title)) BETWEEN 1 AND 100),
                CHECK(length(trim(description)) BETWEEN 1 AND 2000),
                CHECK(price_wei NOT GLOB '*[^0-9]*'),
                CHECK(length(price_wei) > 0),
                CHECK(active IN (0,1))
            )""",
            "CREATE INDEX idx_marketplace_listings_active ON marketplace_listings(active,created_at DESC)",
            "CREATE INDEX idx_marketplace_listings_seller ON marketplace_listings(seller_user_id,created_at DESC)",
            """CREATE TABLE marketplace_purchase_intents(
                intent_id TEXT PRIMARY KEY,
                listing_id TEXT NOT NULL,
                buyer_user_id TEXT NOT NULL,
                seller_user_id TEXT NOT NULL,
                chain_id INTEGER NOT NULL,
                from_address TEXT NOT NULL,
                to_address TEXT NOT NULL,
                amount_wei TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                verified_at TEXT,
                FOREIGN KEY(listing_id) REFERENCES marketplace_listings(listing_id) ON DELETE CASCADE,
                FOREIGN KEY(buyer_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY(seller_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                CHECK(buyer_user_id != seller_user_id),
                CHECK(amount_wei NOT GLOB '*[^0-9]*'),
                CHECK(length(amount_wei) > 0),
                CHECK(expires_at > created_at)
            )""",
            "CREATE INDEX idx_marketplace_intents_buyer ON marketplace_purchase_intents(buyer_user_id,created_at DESC)",
            """CREATE TABLE marketplace_sales(
                sale_id TEXT PRIMARY KEY,
                intent_id TEXT NOT NULL UNIQUE,
                tx_hash TEXT NOT NULL UNIQUE,
                listing_id TEXT NOT NULL,
                buyer_user_id TEXT NOT NULL,
                seller_user_id TEXT NOT NULL,
                chain_id INTEGER NOT NULL,
                from_address TEXT NOT NULL,
                to_address TEXT NOT NULL,
                amount_wei TEXT NOT NULL,
                block_number INTEGER NOT NULL,
                verified_at TEXT NOT NULL,
                FOREIGN KEY(intent_id) REFERENCES marketplace_purchase_intents(intent_id) ON DELETE CASCADE,
                FOREIGN KEY(listing_id) REFERENCES marketplace_listings(listing_id) ON DELETE CASCADE,
                FOREIGN KEY(buyer_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY(seller_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                CHECK(buyer_user_id != seller_user_id),
                CHECK(amount_wei NOT GLOB '*[^0-9]*'),
                CHECK(length(amount_wei) > 0),
                CHECK(block_number >= 0)
            )""",
            "CREATE INDEX idx_marketplace_sales_buyer ON marketplace_sales(buyer_user_id,verified_at DESC)",
            "CREATE INDEX idx_marketplace_sales_seller ON marketplace_sales(seller_user_id,verified_at DESC)",
        ),
    ),
    (
        8,
        "demo_creator_profiles",
        (
            "ALTER TABLE users ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 0 CHECK(is_demo IN (0,1))",
        ),
    ),
    (
        9,
        "simulated_demo_payments",
        (
            """CREATE TABLE demo_payments(
                payment_id TEXT PRIMARY KEY,
                sender_user_id TEXT NOT NULL,
                recipient_user_id TEXT NOT NULL,
                amount_wei TEXT NOT NULL,
                memo TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(sender_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY(recipient_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                CHECK(sender_user_id != recipient_user_id),
                CHECK(amount_wei NOT GLOB '*[^0-9]*'),
                CHECK(length(amount_wei) > 0),
                CHECK(length(trim(memo)) > 0)
            )""",
            "CREATE INDEX idx_demo_payments_activity ON demo_payments(created_at DESC,payment_id)",
        ),
    ),
    (
        10,
        "remove_simulated_demo_payments",
        ("DROP TABLE IF EXISTS demo_payments",),
    ),
    (
        11,
        "developer_social_v2",
        (
            # Developer/remote-worker profile fields.
            "ALTER TABLE users ADD COLUMN skills TEXT NOT NULL DEFAULT '[]'",
            "ALTER TABLE users ADD COLUMN timezone TEXT NOT NULL DEFAULT ''",
            """ALTER TABLE users ADD COLUMN availability TEXT NOT NULL DEFAULT 'none'
            CHECK(availability IN ('none','open_to_work','hiring','open_to_collab'))""",
            # Rich posts: markdown, link, project + evidence snapshot, counters.
            "ALTER TABLE social_posts ADD COLUMN format TEXT NOT NULL DEFAULT 'plain' CHECK(format IN ('plain','markdown'))",
            "ALTER TABLE social_posts ADD COLUMN link_url TEXT",
            "ALTER TABLE social_posts ADD COLUMN project_id TEXT REFERENCES projects(project_id) ON DELETE SET NULL",
            "ALTER TABLE social_posts ADD COLUMN artifact_ref TEXT",
            "ALTER TABLE social_posts ADD COLUMN evidence_supported INTEGER",
            "ALTER TABLE social_posts ADD COLUMN evidence_total INTEGER",
            "ALTER TABLE social_posts ADD COLUMN updated_at TEXT",
            "ALTER TABLE social_posts ADD COLUMN like_count INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE social_posts ADD COLUMN comment_count INTEGER NOT NULL DEFAULT 0",
            """CREATE TABLE post_tags(
                post_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                PRIMARY KEY(post_id,tag),
                FOREIGN KEY(post_id) REFERENCES social_posts(post_id) ON DELETE CASCADE
            )""",
            "CREATE INDEX idx_post_tags_tag ON post_tags(tag,post_id)",
            """CREATE TABLE post_likes(
                post_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(post_id,user_id),
                FOREIGN KEY(post_id) REFERENCES social_posts(post_id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )""",
            "CREATE INDEX idx_post_likes_user ON post_likes(user_id,created_at DESC)",
            """CREATE TABLE post_bookmarks(
                post_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(post_id,user_id),
                FOREIGN KEY(post_id) REFERENCES social_posts(post_id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )""",
            "CREATE INDEX idx_post_bookmarks_user ON post_bookmarks(user_id,created_at DESC)",
            """CREATE TABLE post_comments(
                comment_id TEXT PRIMARY KEY,
                post_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(post_id) REFERENCES social_posts(post_id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                CHECK(length(trim(body)) BETWEEN 1 AND 1000)
            )""",
            "CREATE INDEX idx_post_comments_post ON post_comments(post_id,created_at,comment_id)",
            """CREATE TABLE notifications(
                notification_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                actor_user_id TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('follow','like','comment','tip')),
                post_id TEXT,
                ref_id TEXT,
                created_at TEXT NOT NULL,
                read_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY(actor_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY(post_id) REFERENCES social_posts(post_id) ON DELETE CASCADE,
                CHECK(user_id != actor_user_id)
            )""",
            "CREATE INDEX idx_notifications_user ON notifications(user_id,created_at DESC,notification_id)",
            # Tips can be attached to a post and carry a short public message.
            "ALTER TABLE tip_intents ADD COLUMN post_id TEXT REFERENCES social_posts(post_id) ON DELETE SET NULL",
            "ALTER TABLE tip_intents ADD COLUMN message TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE verified_tips ADD COLUMN post_id TEXT REFERENCES social_posts(post_id) ON DELETE SET NULL",
            "ALTER TABLE verified_tips ADD COLUMN message TEXT NOT NULL DEFAULT ''",
            "CREATE INDEX idx_verified_tips_post ON verified_tips(post_id)",
            "CREATE INDEX idx_verified_tips_sender ON verified_tips(sender_user_id,verified_at DESC)",
        ),
    ),
    (
        12,
        "longer_posts_8000",
        (
            # SQLite cannot alter a CHECK constraint, so rebuild the table. The
            # migrator turns foreign keys OFF around the rebuild so that dropping the
            # old table does not cascade-delete likes, comments and tags.
            """CREATE TABLE social_posts_new(
                post_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL,
                format TEXT NOT NULL DEFAULT 'plain' CHECK(format IN ('plain','markdown')),
                link_url TEXT,
                project_id TEXT REFERENCES projects(project_id) ON DELETE SET NULL,
                artifact_ref TEXT,
                evidence_supported INTEGER,
                evidence_total INTEGER,
                updated_at TEXT,
                like_count INTEGER NOT NULL DEFAULT 0,
                comment_count INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                CHECK(length(trim(body)) BETWEEN 1 AND 8000)
            )""",
            """INSERT INTO social_posts_new
            (post_id,user_id,body,created_at,format,link_url,project_id,artifact_ref,
            evidence_supported,evidence_total,updated_at,like_count,comment_count)
            SELECT post_id,user_id,body,created_at,format,link_url,project_id,artifact_ref,
            evidence_supported,evidence_total,updated_at,like_count,comment_count
            FROM social_posts""",
            "DROP TABLE social_posts",
            "ALTER TABLE social_posts_new RENAME TO social_posts",
            "CREATE INDEX idx_social_posts_feed ON social_posts(created_at DESC,post_id)",
            "CREATE INDEX idx_social_posts_user ON social_posts(user_id,created_at DESC)",
        ),
    ),
    (
        13,
        "background_ai_jobs",
        (
            """CREATE TABLE ai_jobs(
                job_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                project_id TEXT,
                kind TEXT NOT NULL,
                params_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL CHECK(status IN
                    ('queued','running','succeeded','failed','cancelled')),
                progress INTEGER NOT NULL DEFAULT 0 CHECK(progress BETWEEN 0 AND 100),
                step TEXT NOT NULL DEFAULT '',
                result_json TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE SET NULL
            )""",
            "CREATE INDEX idx_ai_jobs_user ON ai_jobs(user_id,created_at DESC)",
            "CREATE INDEX idx_ai_jobs_active ON ai_jobs(status,project_id)",
        ),
    ),
    (
        14,
        "verifiable_publications",
        (
            # An immutable snapshot of what an author published plus the evidence
            # that backed it at that moment. Anyone can read it (public endpoint).
            """CREATE TABLE publications(
                publication_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                project_id TEXT,
                kind TEXT NOT NULL CHECK(kind IN ('case_study','post')),
                artifact_type TEXT,
                title TEXT NOT NULL DEFAULT '',
                content_json TEXT NOT NULL,
                content_sha256 TEXT NOT NULL,
                trust_level TEXT NOT NULL CHECK(trust_level IN ('repository','notes')),
                repository_url TEXT,
                commit_sha TEXT,
                ownership_verified INTEGER NOT NULL DEFAULT 0 CHECK(ownership_verified IN (0,1)),
                claims_json TEXT NOT NULL,
                sources_json TEXT NOT NULL,
                supported INTEGER NOT NULL DEFAULT 0,
                total INTEGER NOT NULL DEFAULT 0,
                method TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                revoked_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE SET NULL
            )""",
            "CREATE INDEX idx_publications_user ON publications(user_id,created_at DESC)",
            "CREATE INDEX idx_publications_project ON publications(project_id,created_at DESC)",
            "ALTER TABLE social_posts ADD COLUMN publication_id TEXT REFERENCES publications(publication_id) ON DELETE SET NULL",
            "CREATE INDEX idx_social_posts_publication ON social_posts(publication_id)",
            # Proof that the author controls the repository (challenge file in the repo).
            """CREATE TABLE project_ownership(
                project_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token TEXT NOT NULL,
                created_at TEXT NOT NULL,
                verified_at TEXT,
                FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )""",
        ),
    ),
)


def migrate(connection: sqlite3.Connection) -> int:
    known = {version: name for version, name, _ in MIGRATIONS}
    ledger_exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
    ).fetchone()
    if ledger_exists:
        recorded = {
            row[0]: row[1]
            for row in connection.execute("SELECT version,name FROM schema_migrations")
        }
        if recorded == known:
            return max(known, default=0)

    # Foreign keys can only be toggled outside a transaction. Table rebuilds need
    # them off; integrity is re-checked before commit.
    connection.execute("PRAGMA foreign_keys=OFF")
    connection.execute("BEGIN IMMEDIATE")
    try:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS schema_migrations(
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )"""
        )
        applied = {
            row[0]: row[1]
            for row in connection.execute("SELECT version,name FROM schema_migrations")
        }
        known_versions = set(known)
        unknown = set(applied) - known_versions
        if unknown:
            raise RuntimeError(
                f"Database contains unknown migration versions: {sorted(unknown)}"
            )

        for version, name, statements in MIGRATIONS:
            if version in applied:
                if applied[version] != name:
                    raise RuntimeError(
                        f"Migration {version} is recorded as {applied[version]!r}, "
                        f"expected {name!r}."
                    )
                continue
            for statement in statements:
                connection.execute(statement)
            connection.execute(
                "INSERT INTO schema_migrations(version,name,applied_at) VALUES(?,?,?)",
                (
                    version,
                    name,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        current = max(known_versions, default=0)
        violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise RuntimeError(
                f"Migration left {len(violations)} foreign-key violation(s)."
            )
        connection.commit()
        return current
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.execute("PRAGMA foreign_keys=ON")
