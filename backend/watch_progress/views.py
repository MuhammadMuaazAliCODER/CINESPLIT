from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.api_serializers import ErrorSerializer
from accounts.permissions import IsAuthenticatedUser
from core.content import ContentIdError
from .serializers import WatchDeleteSerializer, WatchHistoryItemSerializer, WatchHistoryListSerializer, WatchProgressWriteSerializer, WatchQuerySerializer
from .services import WatchError, get_progress, list_history, remove_history, save_progress


class WatchHistoryView(APIView):
    permission_classes = [IsAuthenticatedUser]

    @extend_schema(operation_id="watch_history_list", parameters=[WatchQuerySerializer], responses={200: WatchHistoryListSerializer})
    def get(self, request):
        serializer = WatchQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response({"detail": "Watch query is invalid.", "errors": serializer.errors}, status=400)
        return Response(list_history(request.user.id, **serializer.validated_data))

    @extend_schema(operation_id="watch_progress_save", request=WatchProgressWriteSerializer, responses={200: WatchHistoryListSerializer, 400: ErrorSerializer, 404: ErrorSerializer})
    def post(self, request):
        serializer = WatchProgressWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"detail": "Watch progress is invalid.", "errors": serializer.errors}, status=400)
        try:
            result = save_progress(request.user.id, **serializer.validated_data)
        except ContentIdError as exc:
            return Response({"detail": str(exc)}, status=400)
        if result is None:
            return Response({"detail": "Published content was not found."}, status=404)
        return Response(result)


class WatchHistoryDetailView(APIView):
    permission_classes = [IsAuthenticatedUser]

    @extend_schema(operation_id="watch_progress_get", responses={200: WatchHistoryItemSerializer, 400: ErrorSerializer, 404: ErrorSerializer})
    def get(self, request, content_type, content_id):
        try:
            result = get_progress(request.user.id, content_type, content_id)
        except ContentIdError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(result) if result else Response({"detail": "Published content was not found."}, status=404)

    @extend_schema(operation_id="watch_history_delete", responses={200: WatchDeleteSerializer, 400: ErrorSerializer})
    def delete(self, request, content_type, content_id):
        try:
            remove_history(request.user.id, content_type, content_id)
        except WatchError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response({"deleted": True})
