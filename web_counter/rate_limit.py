"""In-memory token bucket rate limiter per IP address."""

import time
from collections import defaultdict


class RateLimiter:
    """Token bucket rate limiter. Each IP gets `max_requests` tokens per 60s window."""

    def __init__(self, max_requests: int = 60):
        self.max_requests = max_requests
        self._buckets: dict[str, dict] = defaultdict(
            lambda: {"tokens": max_requests, "last_reset": time.time()}
        )

    def check(self, ip: str) -> bool:
        """Check if the IP is allowed to make a request. Returns True if allowed."""
        now = time.time()
        bucket = self._buckets[ip]

        # Reset bucket if the window has passed
        if now - bucket["last_reset"] >= 60:
            bucket["tokens"] = self.max_requests
            bucket["last_reset"] = now

        if bucket["tokens"] > 0:
            bucket["tokens"] -= 1
            return True
        return False
