import secrets

from fastapi import Depends
from fastapi.security import APIKeyHeader

from app.config import Settings, get_settings
from app.errors import DomainError


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(
    supplied_key: str | None = Depends(api_key_header),
    settings: Settings = Depends(get_settings),
) -> None:
    if supplied_key is None or not secrets.compare_digest(
        supplied_key, settings.appointments_api_key
    ):
        raise DomainError(401, "authentication_failed", "Nieprawidłowy lub brakujący klucz API.")
