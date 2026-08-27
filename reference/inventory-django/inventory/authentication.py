import secrets
from dataclasses import dataclass

from django.conf import settings
from rest_framework import authentication, exceptions


@dataclass(frozen=True)
class ServicePrincipal:
    username: str = "api-client"
    is_authenticated: bool = True
    is_anonymous: bool = False


class ApiKeyAuthentication(authentication.BaseAuthentication):
    header_name = "X-API-Key"

    def authenticate(self, request):
        supplied_key = request.headers.get(self.header_name)
        if not supplied_key:
            return None
        if not secrets.compare_digest(supplied_key, settings.INVENTORY_API_KEY):
            raise exceptions.AuthenticationFailed("Nieprawidłowy klucz API.")
        return ServicePrincipal(), None

    def authenticate_header(self, request):
        return self.header_name
