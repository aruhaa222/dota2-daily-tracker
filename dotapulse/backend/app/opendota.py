"""Small OpenDota HTTP client with a short in-memory cache."""
import time
import httpx


class OpenDotaError(Exception):
    pass


class OpenDotaClient:
    BASE_URL = "https://api.opendota.com/api"

    def __init__(self, ttl_seconds: int = 60):
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, tuple[float, object]] = {}

    async def get(self, path: str):
        now = time.monotonic()
        cached = self._cache.get(path)
        if cached and now - cached[0] < self.ttl_seconds:
            return cached[1]
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                response = await client.get(f"{self.BASE_URL}{path}")
            if response.status_code == 404:
                raise OpenDotaError("Игрок или матч не найден в OpenDota.")
            if response.status_code == 429:
                raise OpenDotaError("OpenDota временно ограничила частоту запросов. Попробуй позже.")
            response.raise_for_status()
            data = response.json()
        except OpenDotaError:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise OpenDotaError("Не удалось получить данные OpenDota. Попробуй ещё раз позже.") from exc
        self._cache[path] = (now, data)
        return data
