from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.api_serializers import ErrorSerializer
from accounts.permissions import IsAuthenticatedUser
from core.content import ContentIdError
from .serializers import FavoriteListSerializer, FavoriteQuerySerializer, FavoriteStateSerializer, FavoriteWriteSerializer
from .services import list_favorites, set_favorite


class FavoriteCollectionView(APIView):
    permission_classes = [IsAuthenticatedUser]

    @extend_schema(operation_id="favorites_list", parameters=[FavoriteQuerySerializer], responses={200: FavoriteListSerializer})
    def get(self, request):
        query = FavoriteQuerySerializer(data=request.query_params)
        if not query.is_valid():
            return Response({"detail": "Favorite query is invalid.", "errors": query.errors}, status=400)
        return Response(list_favorites(request.user.id, **query.validated_data))

    @extend_schema(operation_id="favorites_add", request=FavoriteWriteSerializer, responses={200: FavoriteStateSerializer, 400: ErrorSerializer, 404: ErrorSerializer})
    def post(self, request):
        serializer = FavoriteWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"detail": "Favorite data is invalid.", "errors": serializer.errors}, status=400)
        try:
            result = set_favorite(request.user.id, **serializer.validated_data)
        except ContentIdError as exc:
            return Response({"detail": str(exc)}, status=400)
        if result is None:
            return Response({"detail": "Published content was not found."}, status=404)
        return Response({"favorited": True})


class FavoriteDetailView(APIView):
    permission_classes = [IsAuthenticatedUser]

    @extend_schema(operation_id="favorites_state", responses={200: FavoriteStateSerializer, 404: ErrorSerializer})
    def get(self, request, content_type, content_id):
        from .services import is_favorite
        try:
            return Response({"favorited": is_favorite(request.user.id, content_type, content_id)})
        except ContentIdError as exc:
            return Response({"detail": str(exc)}, status=400)

    @extend_schema(operation_id="favorites_remove", responses={200: FavoriteStateSerializer, 400: ErrorSerializer})
    def delete(self, request, content_type, content_id):
        from .services import set_favorite
        try:
            result = set_favorite(request.user.id, content_type, content_id, favorite=False)
        except ContentIdError as exc:
            return Response({"detail": str(exc)}, status=400)
        if result is None:
            return Response({"detail": "Published content was not found."}, status=404)
        return Response({"favorited": False})
