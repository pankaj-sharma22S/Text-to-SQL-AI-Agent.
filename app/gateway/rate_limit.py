import time
from collections import defaultdict, deque

class RateLimiter:
    def __init__(self, limit=10, window_seconds=60):
        self.limit = limit
        self.window_seconds = window_seconds
        self._events = defaultdict(deque)

    def allow(self, user_id: str) -> bool:
        now = time.monotonic()
        events = self._events[user_id]
        while events and events[0] <= now - self.window_seconds:
            events.popleft()
        if len(events) >= self.limit:
            return False
        events.append(now)
        return True
