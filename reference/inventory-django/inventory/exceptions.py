from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler


class DomainConflict(APIException):
    status_code = 409
    default_code = "conflict"
    default_detail = "Operacja powoduje konflikt z bieżącym stanem zasobu."

    def __init__(self, detail=None, code=None):
        super().__init__(detail=detail, code=code)
        self.domain_code = code or self.default_code


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        if isinstance(exc, (IntegrityError, ProtectedError)):
            return Response(
                {
                    "error": {
                        "code": "database_conflict",
                        "message": "Operacja narusza spójność istniejących danych.",
                        "details": None,
                    }
                },
                status=409,
            )
        return response

    if isinstance(exc, DomainConflict):
        code = exc.domain_code
        message = str(exc.detail)
        details = None
    elif response.status_code == 400:
        code = "validation_error"
        message = "Żądanie zawiera nieprawidłowe dane."
        details = response.data
    elif response.status_code == 401:
        code = "authentication_failed"
        message = "Uwierzytelnienie nie powiodło się."
        details = response.data
    elif response.status_code == 403:
        code = "permission_denied"
        message = "Brak uprawnień do wykonania operacji."
        details = response.data
    elif response.status_code == 404:
        code = "not_found"
        message = "Nie znaleziono zasobu."
        details = None
    else:
        code = "api_error"
        message = "Nie udało się wykonać żądania."
        details = response.data

    response.data = {"error": {"code": code, "message": message, "details": details}}
    return response
