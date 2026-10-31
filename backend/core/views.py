from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers

from config.cloudinary_client import is_cloudinary_configured
from config.mongo import MongoConfigurationError, MongoUnavailableError, ping_database


@extend_schema(
    operation_id="health_check",
    summary="Check service dependencies",
    description="Reports application readiness, MongoDB connectivity, and Cloudinary configuration availability.",
    responses={
        200: inline_serializer(name="HealthResponse", fields={
            "status": serializers.ChoiceField(choices=["ok"]),
            "mongodb": serializers.ChoiceField(choices=["connected"]),
            "cloudinary": serializers.ChoiceField(choices=["configured", "not_configured"]),
        }),
        503: inline_serializer(name="HealthUnavailableResponse", fields={
            "status": serializers.ChoiceField(choices=["unavailable", "degraded"]),
            "mongodb": serializers.ChoiceField(choices=["not_configured", "unavailable"]),
            "cloudinary": serializers.ChoiceField(choices=["configured", "not_configured"]),
        }),
    },
)
@api_view(["GET"])
def health_check(request):
    try:
        ping_database()
    except MongoConfigurationError:
        return Response(
            {"status": "unavailable", "mongodb": "not_configured", "cloudinary": "configured" if is_cloudinary_configured() else "not_configured"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except MongoUnavailableError:
        return Response(
            {"status": "degraded", "mongodb": "unavailable", "cloudinary": "configured" if is_cloudinary_configured() else "not_configured"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response({
        "status": "ok",
        "mongodb": "connected",
        "cloudinary": "configured" if is_cloudinary_configured() else "not_configured",
    })
