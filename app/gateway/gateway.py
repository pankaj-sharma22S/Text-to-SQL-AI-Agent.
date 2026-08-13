import asyncio
import json
import logging
import uuid
from types import SimpleNamespace
from dataclasses import dataclass
from app.gateway.cache import ResponseCache
from app.gateway.config import GatewayConfig
from app.gateway.fallback import with_fallback
from app.gateway.gemini import create_gemini
from app.gateway.load_balancer import ProviderLoadBalancer
from app.gateway.rate_limit import RateLimiter
from app.gateway.retry import retry_async
from app.gateway.router import GatewayRoute
from app.gateway.schema_metadata import SchemaMetadata
from app.gateway.timeout import with_timeout
from app.guardrails.input import InputGuardrail

log = logging.getLogger(__name__)

@dataclass(frozen=True)
class GatewayDecision:
    route: GatewayRoute
    text: str
    reason: str
    request_id: str

class AIGateway:
    def __init__(self, config=None, input_guardrail=None):
        self.config = config or GatewayConfig()
        self.input_guardrail = input_guardrail or InputGuardrail()
        self.cache = ResponseCache(self.config.redis_url, self.config.cache_ttl_seconds)
        self.rate_limiter = RateLimiter(self.config.rate_limit_requests, self.config.rate_limit_window_seconds)
        self.chat_balancer = ProviderLoadBalancer(self.config.provider_deployments)
        self.sql_balancer = ProviderLoadBalancer(self.config.provider_deployments)
        self._gemini = None
        self._openrouter = None

    def classify(self, message: str, schema=None, user_id="anonymous") -> GatewayDecision:
        checked = self.input_guardrail.process(message)
        request_id = str(uuid.uuid4())
        lower = checked.text.lower()
        if any(term in lower for term in ("password", "api key", "credential", "secret", "credit card", "bank account")):
            return GatewayDecision(GatewayRoute.blocked, checked.text, "sensitive request", request_id)
        if schema:
            reason = SchemaMetadata(schema).ambiguity_reason(checked.text)
            if reason:
                return GatewayDecision(GatewayRoute.ambiguous, checked.text, reason, request_id)
        if any(term in lower for term in ("sql", "table", "column", "database", "data", "row", "record", "query", "show", "list", "count")):
            return GatewayDecision(GatewayRoute.sql, checked.text, "database request", request_id)
        return GatewayDecision(GatewayRoute.chat, checked.text, "general conversation", request_id)

    def _models(self):
        return self._gemini, self._openrouter

    def _model_for(self, provider):
        if provider == "gemini":
            if self._gemini is None:
                self._gemini = create_gemini(self.config.gemini_model)
            return self._gemini
        if self._openrouter is None:
            from app.gateway.openrouter import create_openrouter
            self._openrouter = create_openrouter(self.config.openrouter_model)
        return self._openrouter

    def _fallback_model_for(self, provider):
        model_name = self.config.gemini_fallback_model if provider == "gemini" else self.config.openrouter_fallback_model
        if not model_name:
            return None
        from app.gateway.gemini import create_gemini
        from app.gateway.openrouter import create_openrouter
        return (create_gemini if provider == "gemini" else create_openrouter)(model_name)

    async def _invoke(self, provider: str, messages, user_id: str, structured=None, config=None):
        if not self.rate_limiter.allow(user_id):
            raise RuntimeError("AI gateway rate limit exceeded")
        model = self._model_for(provider)
        if structured:
            model = model.with_structured_output(structured, method="json_mode")
        prompt_key = json.dumps([(str(role), str(content)) for role, content in messages], sort_keys=True)
        key = self.cache.key(provider, prompt_key)
        cached = self.cache.get(key)
        if cached is not None and not structured:
            return SimpleNamespace(content=cached)
        async def call():
            return await asyncio.to_thread(model.invoke, messages, config=config)
        async def fallback_call():
            fallback = self._fallback_model_for(provider)
            if fallback is None:
                raise RuntimeError("no provider fallback configured")
            fallback_model = fallback.with_structured_output(structured, method="json_mode") if structured else fallback
            return await asyncio.to_thread(fallback_model.invoke, messages, config=config)
        try:
            result = await with_timeout(retry_async(call, self.config.max_retries), self.config.timeout_seconds)
        except Exception:
            if self._fallback_model_for(provider) is None:
                raise
            result = await with_timeout(fallback_call(), self.config.timeout_seconds)
        if not structured:
            self.cache.set(key, str(result.content))
        return result

    def invoke_sync(self, provider, messages, user_id="anonymous", structured=None, config=None):
        return asyncio.run(self._invoke(provider, messages, user_id, structured, config))

    async def chat(self, message: str, user_id="anonymous"):
        gemini, _ = self._models()
        return await self._invoke("gemini", [("system", "Answer general conversation concisely. Never reveal secrets."), ("human", message)], user_id)

    async def clarify(self, message: str, reason: str, user_id="anonymous"):
        return await self._invoke("gemini", [("system", "Ask one concise clarification question."), ("human", f"Request: {message}\nAmbiguity: {reason}")], user_id)

    def sql_model(self):
        return self._model_for("openrouter")

    def gemini_model(self):
        return self._model_for("gemini")

_default_gateway = None

def get_gateway() -> AIGateway:
    global _default_gateway
    if _default_gateway is None:
        _default_gateway = AIGateway()
    return _default_gateway
