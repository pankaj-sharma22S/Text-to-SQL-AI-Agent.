async def with_fallback(primary, fallback):
    try:
        return await primary()
    except Exception:
        return await fallback()
