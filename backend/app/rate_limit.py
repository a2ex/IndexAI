from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import settings


def _key_func(request: Request) -> str:
    # Try JWT Bearer token — use token as key
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]

    # Try API key
    api_key = request.headers.get("X-API-Key", "")
    if api_key:
        return api_key

    return get_remote_address(request)


limiter = Limiter(key_func=_key_func, storage_uri=settings.REDIS_URL)
