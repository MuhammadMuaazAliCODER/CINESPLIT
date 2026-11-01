from rest_framework import serializers

from accounts.serializers import StrictSerializer
from favorites.serializers import FavoriteQuerySerializer, FavoriteItemSerializer


class WatchProgressWriteSerializer(StrictSerializer):
    content_type = serializers.ChoiceField(choices=("movie", "series", "episode", "chapter"))
    content_id = serializers.CharField(max_length=24)
    position = serializers.FloatField(min_value=0)
    duration = serializers.FloatField(min_value=0, required=False, allow_null=True)
    completed = serializers.BooleanField(required=False, default=False)
    watched_at = serializers.DateTimeField(required=False)


class WatchHistoryItemSerializer(serializers.Serializer):
    id = serializers.CharField(required=False)
    content_type = serializers.CharField()
    content_id = serializers.CharField()
    content = FavoriteItemSerializer()
    position = serializers.FloatField()
    duration = serializers.FloatField(allow_null=True)
    completed = serializers.BooleanField()
    last_watched_at = serializers.CharField(allow_null=True, required=False)


class WatchHistoryListSerializer(serializers.Serializer):
    results = WatchHistoryItemSerializer(many=True)
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total = serializers.IntegerField()
    pages = serializers.IntegerField()


class WatchQuerySerializer(FavoriteQuerySerializer):
    continue_watching = serializers.BooleanField(required=False, default=False)


class WatchDeleteSerializer(serializers.Serializer):
    deleted = serializers.BooleanField()
