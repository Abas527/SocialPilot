import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    llm_provider: str = os.getenv("LLM_PROVIDER", "ollama")
    llm_model: str = os.getenv("LLM_MODEL", "qwen2.5-coder:7b")
    llm_timeout_s: float = float(os.getenv("LLM_TIMEOUT_S", "240"))
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    # Ollama defaults to a small context window; evidence-heavy prompts need more.
    case_study_chunked: bool = os.getenv("CASE_STUDY_CHUNKED", "1") == "1"
    llm_num_ctx: int = int(os.getenv("LLM_NUM_CTX", "8192"))
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.4"))
    llm_max_retries: int = int(os.getenv("LLM_MAX_RETRIES", "2"))
    llm_retry_backoff_s: float = float(os.getenv("LLM_RETRY_BACKOFF_S", "1.0"))
    ai_workers: int = int(os.getenv("AI_WORKERS", "2"))
    ai_max_active_jobs_per_user: int = int(os.getenv("AI_MAX_ACTIVE_JOBS_PER_USER", "2"))
    ai_daily_job_limit: int = int(os.getenv("AI_DAILY_JOB_LIMIT", "60"))
    use_embeddings: bool = os.getenv("USE_EMBEDDINGS", "0") == "1"
    embed_model: str = os.getenv("EMBED_MODEL", "nomic-embed-text")
    github_token: str = os.getenv("GITHUB_TOKEN", "")
    db_path: str = os.getenv("DB_PATH", "data/socialpilot.db")
    db_url: str = os.getenv("DB_URL")
    db_auth_token: str = os.getenv("DB_AUTH_TOKEN")
    auth_session_ttl_hours: int = int(os.getenv("AUTH_SESSION_TTL_HOURS", "24"))
    email_verification_ttl_hours: int = int(
        os.getenv("EMAIL_VERIFICATION_TTL_HOURS", "24")
    )
    email_provider: str = os.getenv("EMAIL_PROVIDER", "smtp").strip().lower()
    brevo_api_key: str = os.getenv("BREVO_API_KEY", "")
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from: str = os.getenv("SMTP_FROM", "")
    smtp_use_ssl: bool = os.getenv("SMTP_USE_SSL", "0") == "1"
    smtp_starttls: bool = os.getenv("SMTP_STARTTLS", "1") == "1"
    smtp_timeout_s: float = float(os.getenv("SMTP_TIMEOUT_S", "10"))
    public_api_url: str = os.getenv("PUBLIC_API_URL", "http://localhost:8000")
    https_redirect_enabled: bool = os.getenv("HTTPS_REDIRECT", "0") == "1"
    hsts_max_age: int = int(os.getenv("HSTS_MAX_AGE", "31536000"))
    sepolia_rpc_url: str = os.getenv("SEPOLIA_RPC_URL", "")
    sepolia_min_confirmations: int = int(os.getenv("SEPOLIA_MIN_CONFIRMATIONS", "2"))
    tip_intent_ttl_minutes: int = int(os.getenv("TIP_INTENT_TTL_MINUTES", "30"))
    tip_max_wei: int = int(os.getenv("TIP_MAX_WEI", "1000000000000000000"))
    demo_seed_enabled: bool = os.getenv("DEMO_SEED_ENABLED", "0") == "1"

    # Web security / abuse protection
    cors_origins: tuple[str, ...] = tuple(
        o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()
    )
    rate_limit_enabled: bool = os.getenv("RATE_LIMIT_ENABLED", "1") == "1"
    trust_proxy_headers: bool = os.getenv("TRUST_PROXY_HEADERS", "0") == "1"
    auth_rate_limit_per_min: int = int(os.getenv("AUTH_RATE_LIMIT_PER_MIN", "10"))
    ai_rate_limit_per_min: int = int(os.getenv("AI_RATE_LIMIT_PER_MIN", "6"))
    export_rate_limit_per_min: int = int(os.getenv("EXPORT_RATE_LIMIT_PER_MIN", "10"))
    write_rate_limit_per_min: int = int(os.getenv("WRITE_RATE_LIMIT_PER_MIN", "60"))

    # Ingestion limits
    max_files: int = 25
    max_file_bytes: int = 60_000
    max_total_bytes: int = 400_000
    http_timeout_s: float = 15.0

    # RAG
    chunk_chars: int = 1200
    top_k: int = 6


settings = Settings()
