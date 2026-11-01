from rest_framework import serializers

from accounts.serializers import StrictSerializer


class FavoriteWriteSerializer(StrictSerializer):
    content_type = serializers.ChoiceField(choices=("movie", "series", "episode", "chapter"))
    content_id = serializers.CharField(max_length=24)


class FavoriteQuerySerializer(StrictSerializer):
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=50, default=20)


class FavoriteItemSerializer(serializers.Serializer):
    content_type = serializers.CharField()
    content_id = serializers.CharField()
    title = serializers.CharField()
    slug = serializers.CharField()
    url = serializers.CharField()
    poster_url = serializers.CharField(allow_blank=True)
    release_year = serializers.IntegerField(allow_null=True)
    favorited_at = serializers.DateTimeField(required=False)


class FavoriteListSerializer(serializers.Serializer):
    results = FavoriteItemSerializer(many=True)
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total = serializers.IntegerField()
    pages = serializers.IntegerField()


class FavoriteStateSerializer(serializers.Serializer):
    favorited = serializers.BooleanField()
