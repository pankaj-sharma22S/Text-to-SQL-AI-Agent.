from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class GatewayConfig:
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    gemini_fallback_model: str | None = os.getenv("GEMINI_FALLBACK_MODEL")
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-20b:free")
    openrouter_fallback_model: str | None = os.getenv("OPENROUTER_FALLBACK_MODEL")
    redis_url: str | None = os.getenv("REDIS_URL")
    cache_ttl_seconds: int = int(os.getenv("AI_CACHE_TTL_SECONDS", "300"))
    rate_limit_requests: int = int(os.getenv("AI_RATE_LIMIT_REQUESTS", "10"))
    rate_limit_window_seconds: int = int(os.getenv("AI_RATE_LIMIT_WINDOW_SECONDS", "60"))
    timeout_seconds: float = float(os.getenv("AI_TIMEOUT_SECONDS", "30"))
    max_retries: int = int(os.getenv("AI_MAX_RETRIES", "2"))
    provider_deployments: tuple[str, ...] = tuple(x.strip() for x in os.getenv("AI_PROVIDER_DEPLOYMENTS", "primary").split(",") if x.strip())
