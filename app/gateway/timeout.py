import asyncio

async def with_timeout(awaitable, seconds: float):
    return await asyncio.wait_for(awaitable, timeout=seconds)
