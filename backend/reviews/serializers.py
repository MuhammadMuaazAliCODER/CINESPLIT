from rest_framework import serializers

from accounts.serializers import StrictSerializer
from favorites.serializers import FavoriteQuerySerializer


class ReviewWriteSerializer(StrictSerializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    body = serializers.CharField(max_length=4000, required=False, allow_blank=True, default="", trim_whitespace=True)


class ReviewSerializer(serializers.Serializer):
    id = serializers.CharField()
    user_id = serializers.CharField()
    username = serializers.CharField()
    rating = serializers.IntegerField()
    body = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class ReviewQuerySerializer(FavoriteQuerySerializer):
    pass


class ReviewListSerializer(serializers.Serializer):
    results = ReviewSerializer(many=True)
    average_rating = serializers.FloatField(allow_null=True)
    rating_count = serializers.IntegerField()
    current_review = ReviewSerializer(allow_null=True)
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    pages = serializers.IntegerField()


class ReviewDeleteSerializer(serializers.Serializer):
    deleted = serializers.BooleanField()
