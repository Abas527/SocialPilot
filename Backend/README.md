# SocialPilot AI — backend + RAG scaffold

Pipeline: ingest → chunk/index (RAG) → analyze → generate → verify claims → store → export.

```
ollama pull qwen2.5-coder:7b
pip install -r requirements.txt
cp .env.example .env        # configure Ollama or hosted model
pytest -q
uvicorn api.main:app --reload   # docs at http://localhost:8000/docs
```

## Project and RAG API

Project imports persist the ingested source documents and their line-aware chunks
in SQLite. Analysis, generation, and search use the persisted chunks, so retrieval
survives API restarts and does not need to rechunk each project on every request.
Legacy projects are reindexed automatically when first accessed if their chunk
index is missing or uses a different configured chunk size.

- `POST /projects/import` — import exactly one public GitHub repository or pasted
  project/work notes. Notes can describe a remote-work project, role, constraints,
  decisions, and verifiable outcomes; add a Markdown heading to name the project.
- `GET /projects` and `GET /projects/{project_id}` — list or retrieve a project.
- `GET /projects/{project_id}/workflow` — summarize source, analysis, RAG, and saved artifact state.
- `GET /projects/{project_id}/sources` — list source metadata without returning file contents.
- `DELETE /projects/{project_id}` — remove a project, its sources, artifacts, and RAG chunks.
- `GET /projects/{project_id}/rag` — report chunk count, chunk size, and index time.
- `POST /projects/{project_id}/rag/reindex` — rebuild that project's persisted chunks.
- `GET /projects/{project_id}/rag/chunks?limit=50&offset=0&path=README.md` — inspect
  persisted chunks with source and line metadata.
- `GET /projects/{project_id}/rag/search?q=...&limit=6` — return matching text and
  source path/line citations; `limit` can be 1–20.
- `POST /projects/{project_id}/analyze`, `/post/{angle}` (`/linkedin/{angle}` remains as an alias), and `/case-study` —
  analyze or generate content from the stored project.
- `POST /projects/{project_id}/workflow/run` — run analysis and any requested
  post angles and/or case study in one call. Example:

  ```json
  {
    "linkedin_angles": ["technical_lesson", "engineering_decision"],
    "include_case_study": true,
    "user_context": "",
    "reanalyze": true
  }
  ```

  Analysis is refreshed by default. Set `reanalyze` to `false` to reuse a saved
  profile. Each requested output reports `generated` or `failed` independently,
  so one unsupported angle does not discard other successful outputs.
- `GET /projects/{project_id}/artifacts/{artifact_type}` — retrieve generated,
  edited, and current artifact versions.
- `PUT /projects/{project_id}/artifacts/{artifact_type}` — save an edited version.
- `POST /projects/{project_id}/artifacts/{artifact_type}/revert` — discard edits and restore
  the generated version.
- `POST /projects/{project_id}/artifacts/case_study/export/markdown` or
  `/export/pdf` — export the current saved case-study version.

Project listing supports `limit`, `offset`, and `q` filtering. Pagination limits
for project/chunk lists are capped at 100.

Interactive OpenAPI docs are available at `http://localhost:8000/docs`.

## Database foundation

The SQLite schema is upgraded automatically through transactional, versioned
migrations whenever the storage layer opens the database. Existing project,
source, artifact, and RAG data is preserved when upgrading the legacy schema.
`GET /health` reports SQLite readiness and the applied schema version.

## Authentication and authorization

- `POST /auth/register` — create an account (password must be at least 12 characters) and send a verification email.
- `POST /auth/verify-email` — verify the account using `{"token":"..."}`.
- `POST /auth/resend-verification` — request a replacement verification email.
- `POST /auth/login` — exchange email/password for a bearer token.
- `GET /auth/me` — return the authenticated account.
- `POST /auth/logout` — revoke the current bearer token.

For Brevo, set `EMAIL_PROVIDER=brevo`, `BREVO_API_KEY`, and `SMTP_FROM` in
`.env`; `SMTP_FROM` must be a sender verified in Brevo. The backend sends each
verification message through Brevo's transactional email endpoint
(`POST /v3/smtp/email`) with the API key in the `api-key` header. Do not use the
campaign API for account verification emails. For SMTP instead, set
`EMAIL_PROVIDER=smtp`, `SMTP_HOST`, `SMTP_FROM`, and the SMTP transport
settings. SMTP uses STARTTLS by default; alternatively set `SMTP_USE_SSL=1` and
`SMTP_STARTTLS=0`. SMTP credentials are optional for trusted relay servers, but
`SMTP_USERNAME` and `SMTP_PASSWORD` must be supplied together.
`PUBLIC_API_URL` must use HTTPS except for loopback development URLs.
Verification links expire after `EMAIL_VERIFICATION_TTL_HOURS`
(default `24`); resending invalidates earlier links. Links keep the token in the
URL fragment, so it is not sent in the initial HTTP request or normal access
logs. The confirmation page requires an explicit button click before verifying.
Unverified accounts cannot log in. Passwords use salted scrypt hashes; access
tokens are random and only their SHA-256 hashes are persisted. Access tokens
expire after `AUTH_SESSION_TTL_HOURS` (default `24`).

All `/projects` endpoints require `Authorization: Bearer <access_token>`.
Projects imported through the API are owned by the authenticated user; list and
project-specific operations are restricted to that owner. Requests for projects
that do not belong to the caller return `404` to avoid disclosing project
existence. Projects created before ownership was enabled remain unowned and are
not automatically assigned to the first account.

The standalone `/export/markdown`, `/export/pdf`, and `/health` endpoints do not
access account-owned project data and do not require authentication. Use HTTPS
and add rate limiting before exposing registration or login to an untrusted
network. The resend endpoint uses a generic response for unknown or already
verified addresses to reduce account enumeration.

Interactive OpenAPI docs are available at `http://localhost:8000/docs`; use
**Authorize** there with the returned bearer token to call protected endpoints.

## HTTPS deployment

For local development, leave `HTTPS_REDIRECT=0`. In production, prefer TLS
termination at a trusted reverse proxy and bind Uvicorn to loopback:

```powershell
$env:API_DOMAIN = "api.example.com"
caddy run --config deploy\Caddyfile
```

Caddy obtains and renews certificates for `API_DOMAIN` and proxies to Uvicorn.
Run the API in another process bound to `127.0.0.1:8000`:

```powershell
uvicorn api.main:app --host 127.0.0.1 --port 8000 `
  --proxy-headers --forwarded-allow-ips=127.0.0.1
```

Set `HTTPS_REDIRECT=1`, `PUBLIC_API_URL=https://api.example.com`, and `SMTP_*`
in `.env`. Uvicorn trusts only the local proxy address here so the app can
recognize Caddy's HTTPS scheme; only trust proxy addresses that you control.

Direct Uvicorn TLS is also supported when certificate and private-key files are
managed separately:

```powershell
uvicorn api.main:app --host 0.0.0.0 --port 8443 `
  --ssl-certfile C:\certs\fullchain.pem `
  --ssl-keyfile C:\certs\privkey.pem
```

Set `HTTPS_REDIRECT=1` and `PUBLIC_API_URL=https://your-host:8443` for this
mode too. HSTS is sent only on HTTPS responses; configure its duration using
`HSTS_MAX_AGE` (default one year). Do not enable HSTS for plain-HTTP local
development.

## Social features, Sepolia tips, and marketplace

The authenticated community API and workspace provide:

- `GET/PUT /social/profile` — view or update your public username, display name, and bio.
- `GET /social/profiles?q=...` and `GET /social/profiles/{username}` — discover creators.
- `POST/DELETE /social/follow/{username}` — follow or unfollow a creator.
- `GET /social/feed` — view your own updates and updates from creators you follow.
- `GET /social/discover` — view public updates from other creators, whether or not you follow them.
- `POST /social/posts` and `DELETE /social/posts/{post_id}` — explicitly publish or remove an update. Projects and generated content are never shared automatically.
- `POST /wallet/challenge` and `POST /wallet/verify` — prove EVM wallet ownership by signing a short-lived message; no gas or transaction is required.
- `POST /tips/prepare` — prepare a native Sepolia ETH transfer to a creator with a verified recipient wallet.
- `POST /tips/{intent_id}/verify` — verify a submitted transaction hash against the configured Sepolia RPC.
- `GET /tips/received` — list server-verified incoming tips.
- `GET /marketplace/listings?q=...&product_type=plugin|library|agent` — browse
  active creator listings. Public catalog responses never contain delivery links.
- `GET /marketplace/listings/{listing_id}` — retrieve an active listing.
- `GET /marketplace/mine` — list the caller's listings.
- `POST /marketplace/listings` — create a plugin, library, or agent listing with
  an ETH price and seller-provided HTTPS delivery URL. The seller must have a
  verified wallet.
- `DELETE /marketplace/listings/{listing_id}` — deactivate the caller's listing;
  verified buyers retain access.
- `POST /marketplace/listings/{listing_id}/purchase` — prepare a direct native
  Sepolia ETH transfer to the creator's verified wallet.
- `POST /marketplace/purchases/{intent_id}/verify` — verify the transaction,
  receipt status, exact sender/recipient/value, chain, and configured
  confirmation depth.
- `GET /marketplace/purchases` — list verified purchases without delivery URLs.
- `GET /marketplace/purchases/{sale_id}` — return the delivery URL only to the
  authenticated buyer who owns that verified purchase.

### Opt-in demo creators

Sample creators, community posts, and plugin/library/agent listings can be added
to a demo database through the authenticated `POST /demo/seed` endpoint. Enable
the endpoint with `DEMO_SEED_ENABLED=1`, restart the API, then invoke it once
(for example, using **Authorize** and **Try it out** at `/docs`). The operation
is idempotent. Seeded accounts are clearly marked as samples, cannot sign in,
and have no verified wallets; sample marketplace listings are preview-only and
cannot be purchased. Leave the setting at its default (`0`) outside demo
environments. `GET /demo/status` reports whether seeding is enabled.

Configure `SEPOLIA_RPC_URL` with a trusted HTTPS RPC endpoint. The API returns
transaction fields for the browser wallet to submit; SocialPilot never receives
private keys or signs, sends, escrows, or holds funds. Marketplace payments go
directly to sellers and cannot be refunded by SocialPilot. The platform does not
host or inspect seller downloads, guarantee their contents, or enforce that a
seller-provided URL is private; sellers should use access-controlled or
single-use links. Marketplace and tip transaction hashes cannot be claimed twice.
All current marketplace payments use Sepolia test ETH, not real funds. Wallet addresses must first be
proved by signature and can only be linked to one account. Tip intents expire
after `TIP_INTENT_TTL_MINUTES` (default 30), require sender and recipient wallet
proof, and enforce `TIP_MAX_WEI` (default 1 test ETH). A tip is recorded only
after server-side checks confirm Sepolia chain ID, transaction sender,
recipient, exact value, successful receipt, and the configured confirmation
count. Replayed transaction hashes are rejected.

This first version uses direct native ETH transfers, which do not emit a
contract `Tip` event. The API verifies the canonical transaction and successful
receipt instead. It is testnet functionality only; do not send mainnet assets.

The backend defaults to Ollama at `http://localhost:11434` with the `qwen2.5-coder:7b`
model. Start Ollama before running the API; set `LLM_MODEL` in `.env` to override it.

Project analysis stores findings with source citations and a preliminary lexical
support status. Post and case-study generation use only supported findings;
if a saved profile predates this finding data, run project analysis again before
generating content. Lexical matching is a review aid, not proof that a claim is
true.
If Qwen's findings do not pass citation checks, analysis can fall back to
conservative language/file-format facts taken from source filename extensions.
Engineering-decision posts are generated only when analysis has a supported
decision finding; technology descriptions alone are not treated as decisions.

For trusted local development code, call `core.pipeline.import_local_project(path)`
from Python to ingest an on-disk project. Local filesystem import is intentionally
not exposed through the HTTP API.

Post drafts and case studies include `verified_claims` and a `review_status`. The status
`preliminary_support` means every extracted statement passed lexical evidence
matching; it is not proof of truth or publication approval. Review source excerpts
before using a draft. `needs_review` indicates that at least one statement needs
human review or that no statements could be checked.

- `core/rag/` — line-aware chunking, BM25, optional Ollama embeddings, RRF hybrid retriever
- `core/evidence.py` — claim -> source excerpt checks, invented-number detection
- `core/pipeline.py` — what any frontend should call

## Community API (v0.2)

All routes require `Authorization: Bearer <token>`. Lists use `limit` (1-50) and `offset`.

| Area | Endpoints |
|---|---|
| Posts | `POST /social/posts` (`body`, `format: plain\|markdown`, `tags[≤5]`, `link_url`, `project_id`, `artifact_ref`), `GET /social/posts?tag=&author=&scope=&sort=new\|top`, `GET/PUT/DELETE /social/posts/{id}`, `GET /social/profiles/{username}/posts`, `GET /social/trending/tags` |
| Engagement | `POST/DELETE /social/posts/{id}/like`, `POST/DELETE /social/posts/{id}/bookmark`, `GET /social/bookmarks`, `GET/POST /social/posts/{id}/comments`, `DELETE /social/comments/{id}` |
| Profiles | `PUT /social/profile` now also accepts `skills[]`, `timezone`, `availability`; `GET /social/profiles/{username}/followers\|following` |
| Notifications | `GET /notifications`, `GET /notifications/unread-count`, `POST /notifications/read` |
| Tips | `POST /tips/prepare` accepts `post_id` (recipient derived) and `message`; `GET /tips/sent`, `GET /social/posts/{id}/tips`, `GET /config/chain` |

A post with `project_id` + `artifact_ref` stores a snapshot of how many of the
artifact's claims were evidence-`supported` when published (`post.evidence`).

Security/ops: `/export/*` now requires login; per-IP limits on `/auth/*`, per-user
limits on AI, export and write endpoints (see `.env.example`); set `CORS_ORIGINS`
only if the frontend is served from a different origin than the API.

## Background AI jobs (v0.3)

Slow model work runs off the request thread. `POST /jobs` returns `202` with a job;
poll `GET /jobs/{id}` (`status`, `progress` 0-100, `step`, `result`/`error`) and
`POST /jobs/{id}/cancel` to stop it (running jobs stop at the next checkpoint).

| `kind` | needs | result |
|---|---|---|
| `workflow` | `project_id`, `angles[]`, `include_case_study`, `reanalyze` | same shape as `/workflow/run` |
| `analyze` / `case_study` | `project_id` | profile / artifact |
| `post` (alias `linkedin`) | `project_id`, `angle`, optional `post_format` | artifact |
| `community_post` | `project_id`, `style: show_and_tell\|devlog\|til\|ask` | Markdown post + tags + claim check |
| `improve_post` | `text`, `goal: clarity\|concise\|friendly\|technical` | improved text (code blocks guaranteed unchanged) |
| `suggest_tags` | `text` | `{tags[]}` |
| `summarize_thread` | `post_id` | `{tldr, key_points, open_questions}` |

Limits: `AI_MAX_ACTIVE_JOBS_PER_USER`, one active job per project, `AI_DAILY_JOB_LIMIT`.
Jobs interrupted by a restart are marked failed on startup. Posts may now be up to 8000 characters.
