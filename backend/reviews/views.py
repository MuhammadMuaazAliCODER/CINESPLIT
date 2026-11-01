from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.api_serializers import ErrorSerializer
from accounts.permissions import IsAuthenticatedUser
from core.content import ContentIdError
from .serializers import ReviewDeleteSerializer, ReviewListSerializer, ReviewQuerySerializer, ReviewSerializer, ReviewWriteSerializer
from .services import ReviewError, create_review, delete_review, review_summary, update_review


class ContentReviewsView(APIView):
    def get_permissions(self):
        return [IsAuthenticatedUser()] if self.request.method == "POST" else [AllowAny()]

    @extend_schema(operation_id="content_reviews_list", parameters=[ReviewQuerySerializer], responses={200: ReviewListSerializer, 400: ErrorSerializer, 404: ErrorSerializer})
    def get(self, request, content_type, content_id):
        query = ReviewQuerySerializer(data=request.query_params)
        if not query.is_valid():
            return Response({"detail": "Review query is invalid.", "errors": query.errors}, status=400)
        try:
            user_id = request.user.id if request.user.is_authenticated else None
            result = review_summary(content_type, content_id, user_id=user_id, **query.validated_data)
        except ContentIdError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(result) if result else Response({"detail": "Published content was not found."}, status=404)

    @extend_schema(operation_id="content_review_create", request=ReviewWriteSerializer, responses={201: ReviewSerializer, 400: ErrorSerializer, 401: ErrorSerializer, 404: ErrorSerializer, 409: ErrorSerializer})
    def post(self, request, content_type, content_id):
        serializer = ReviewWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"detail": "Review data is invalid.", "errors": serializer.errors}, status=400)
        try:
            result = create_review(request.user.id, request.user.username, content_type, content_id, **serializer.validated_data)
        except ContentIdError as exc:
            return Response({"detail": str(exc)}, status=400)
        except ReviewError as exc:
            return Response({"detail": str(exc)}, status=409)
        return Response(result, status=201) if result else Response({"detail": "Published content was not found."}, status=404)


class ReviewDetailView(APIView):
    permission_classes = [IsAuthenticatedUser]

    @extend_schema(operation_id="content_review_update", request=ReviewWriteSerializer, responses={200: ReviewSerializer, 400: ErrorSerializer, 404: ErrorSerializer})
    def patch(self, request, content_type, content_id, review_id):
        serializer = ReviewWriteSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({"detail": "Review data is invalid.", "errors": serializer.errors}, status=400)
        if not serializer.validated_data:
            return Response({"detail": "Provide a rating or review body."}, status=400)
        try:
            result = update_review(request.user.id, content_type, content_id, review_id, serializer.validated_data)
        except (ReviewError, ContentIdError) as exc:
            return Response({"detail": str(exc)}, status=400 if isinstance(exc, ContentIdError) else 404)
        return Response(result) if result else Response({"detail": "Published content was not found."}, status=404)

    @extend_schema(operation_id="content_review_delete", responses={200: ReviewDeleteSerializer, 404: ErrorSerializer})
    def delete(self, request, content_type, content_id, review_id):
        try:
            deleted = delete_review(request.user.id, content_type, content_id, review_id)
        except (ReviewError, ContentIdError) as exc:
            return Response({"detail": str(exc)}, status=400 if isinstance(exc, ContentIdError) else 404)
        return Response({"deleted": deleted})
