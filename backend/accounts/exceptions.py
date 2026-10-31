from django.core.exceptions import ImproperlyConfigured
from pymongo.errors import PyMongoError
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler


def safe_exception_handler(exc, context):
    if isinstance(exc, PyMongoError):
        return Response({"code": "database_unavailable", "detail": "The service is temporarily unavailable."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    if isinstance(exc, ImproperlyConfigured):
        return Response({"code": "service_misconfigured", "detail": "The service is temporarily unavailable."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    response = exception_handler(exc, context)
    if response is not None and isinstance(exc, APIException) and response.status_code >= 500:
        response.data = {"code": "server_error", "detail": "The service encountered an unexpected error."}
    return response
