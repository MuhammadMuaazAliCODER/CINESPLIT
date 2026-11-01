from drf_spectacular.utils import extend_schema
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.api_serializers import ErrorSerializer
from accounts.permissions import IsAdministrator, IsAuthenticatedUser
from .serializers import MediaAssociationsSerializer, MediaAssociationSerializer, MediaLibraryResponseSerializer, MediaUploadSerializer
from .services import MAX_IMAGE_SIZE, MAX_VIDEO_SIZE, MediaConfigurationError, MediaError, get_associations, list_media, upload_and_associate
from rest_framework import serializers
from accounts.serializers import StrictSerializer


class AdminContentMediaView(APIView):
    permission_classes = [IsAuthenticatedUser, IsAdministrator]

    @extend_schema(operation_id="admin_content_media_get", responses={200: MediaAssociationsSerializer, 400: ErrorSerializer, 404: ErrorSerializer})
    def get(self, request, content_type, content_id):
        try:
            return Response(get_associations(content_type, content_id))
        except MediaError as exc:
            code = 404 if "not found" in str(exc).lower() else 400
            return Response({"detail": str(exc)}, status=code)



class AdminContentMediaUploadView(APIView):
    permission_classes = [IsAuthenticatedUser, IsAdministrator]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(operation_id="admin_content_media_upload", request=MediaUploadSerializer, responses={200: MediaAssociationSerializer, 400: ErrorSerializer, 403: ErrorSerializer, 404: ErrorSerializer, 502: ErrorSerializer})
    def post(self, request, content_type, content_id, role):
        limit = MAX_VIDEO_SIZE if role == "video" else MAX_IMAGE_SIZE
        try:
            if int(request.META.get("CONTENT_LENGTH", "0")) > limit + 1024 * 1024:
                return Response({"detail": "Upload exceeds the maximum allowed size."}, status=400)
        except (TypeError, ValueError):
            return Response({"detail": "Upload size is invalid."}, status=400)
        serializer = MediaUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"detail": "Upload data is invalid.", "errors": serializer.errors}, status=400)
        try:
            result = upload_and_associate(content_type, content_id, role, serializer.validated_data["file"], request.user.id)
            return Response(MediaAssociationSerializer(result).data)
        except MediaConfigurationError as exc:
            return Response({"detail": str(exc)}, status=503)
        except MediaError as exc:
            status_code = 404 if "not found" in str(exc).lower() else 400
            if "could not upload" in str(exc).lower() or "could not be associated" in str(exc).lower():
                status_code = 502
            return Response({"detail": str(exc)}, status=status_code)


class MediaLibraryQuerySerializer(StrictSerializer):
    page = serializers.IntegerField(required=False, min_value=1, max_value=100, default=1)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=50, default=20)


class AdminMediaLibraryView(APIView):
    permission_classes = [IsAuthenticatedUser, IsAdministrator]

    @extend_schema(operation_id="admin_media_library", parameters=[MediaLibraryQuerySerializer], responses={200: MediaLibraryResponseSerializer})
    def get(self, request):
        query = MediaLibraryQuerySerializer(data=request.query_params)
        if not query.is_valid():
            return Response({"detail": "Media query is invalid.", "errors": query.errors}, status=400)
        return Response(list_media(**query.validated_data))
