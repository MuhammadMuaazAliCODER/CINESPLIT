from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.api_serializers import ErrorSerializer
from .discovery import discover
from .serializers import DiscoveryListSerializer, DiscoveryQuerySerializer


class DiscoveryView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(operation_id="discovery_search", parameters=[DiscoveryQuerySerializer], responses={200: DiscoveryListSerializer, 400: ErrorSerializer})
    def get(self, request):
        serializer = DiscoveryQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response({"detail": "Discovery filters are invalid.", "errors": serializer.errors}, status=400)
        return Response(discover(serializer.validated_data))


class FeaturedContentView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(operation_id="discovery_featured", responses={200: DiscoveryListSerializer})
    def get(self, request):
        return Response(discover({"page_size": 12}, featured=True))


class LatestContentView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(operation_id="discovery_latest", responses={200: DiscoveryListSerializer})
    def get(self, request):
        return Response(discover({"page_size": 12}, latest=True))
