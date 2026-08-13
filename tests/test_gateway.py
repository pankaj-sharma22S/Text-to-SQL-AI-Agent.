import asyncio
from app.gateway.cache import ResponseCache
from app.gateway.rate_limit import RateLimiter
from app.gateway.gateway import AIGateway
from app.gateway.router import GatewayRoute
from app.schemas.database import ColumnInfo, DatabaseSchema, TableInfo

def schema():
    return DatabaseSchema(tables=[TableInfo(name="branches", columns=[ColumnInfo(name="revenue", data_type="numeric"), ColumnInfo(name="profit", data_type="numeric")])])

def test_gateway_routes_and_schema_ambiguity():
    gateway = AIGateway()
    assert gateway.classify("Hello").route == GatewayRoute.chat
    assert gateway.classify("Show the best branch", schema()).route == GatewayRoute.ambiguous
    assert gateway.classify("List branch revenue", schema()).route == GatewayRoute.sql

def test_cache_and_rate_limit():
    cache = ResponseCache(ttl_seconds=60)
    key = cache.key("gemini", "hello")
    cache.set(key, "cached")
    assert cache.get(key) == "cached"
    limiter = RateLimiter(limit=1, window_seconds=60)
    assert limiter.allow("user") is True
    assert limiter.allow("user") is False

def test_fallback_module():
    from app.gateway.fallback import with_fallback
    async def primary(): raise RuntimeError("down")
    async def fallback(): return "ok"
    assert asyncio.run(with_fallback(primary, fallback)) == "ok"
