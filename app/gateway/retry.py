import asyncio
import logging

log = logging.getLogger(__name__)

async def retry_async(operation, max_retries: int, delay: float = 0.25):
    last = None
    for attempt in range(max_retries + 1):
        try:
            return await operation()
        except Exception as exc:
            last = exc
            if attempt >= max_retries:
                raise
            log.warning("gateway provider retry %s/%s: %s", attempt + 1, max_retries, type(exc).__name__)
            await asyncio.sleep(delay * (2 ** attempt))
    raise last
