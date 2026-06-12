import time
from collections import defaultdict

from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    def __init__(self, max_attempts: int = 5, window_seconds: int = 900) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, list[float]] = defaultdict(list)

    def _cleanup(self, key: str) -> None:
        now = time.time()
        cutoff = now - self.window_seconds
        self._attempts[key] = [t for t in self._attempts[key] if t > cutoff]

    def check(self, request: Request) -> None:
        ip = request.client.host if request.client else "unknown"
        self._cleanup(ip)

        if len(self._attempts[ip]) >= self.max_attempts:
            retry_after = int(
                self.window_seconds
                - (time.time() - self._attempts[ip][0])
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiados intentos. Intente de nuevo más tarde.",
                headers={"Retry-After": str(max(retry_after, 1))},
            )

        self._attempts[ip].append(time.time())


auth_rate_limiter = InMemoryRateLimiter(max_attempts=5, window_seconds=900)
