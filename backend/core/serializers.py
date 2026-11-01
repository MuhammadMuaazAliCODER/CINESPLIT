from rest_framework import serializers

from accounts.serializers import StrictSerializer


class DiscoveryQuerySerializer(StrictSerializer):
    search = serializers.CharField(required=False, max_length=120, allow_blank=True, trim_whitespace=True)
    genre = serializers.CharField(required=False, max_length=50, allow_blank=True, trim_whitespace=True)
    content_type = serializers.ChoiceField(required=False, choices=("movie", "series"))
    release_year = serializers.IntegerField(required=False, min_value=1870, max_value=2100)
    sort = serializers.ChoiceField(required=False, choices=("-release_year", "release_year", "title", "-title", "-created_at"), default="-release_year")
    page = serializers.IntegerField(required=False, min_value=1, max_value=100, default=1)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=25, default=20)


class DiscoveryItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    content_type = serializers.CharField()
    title = serializers.CharField()
    slug = serializers.CharField()
    short_description = serializers.CharField(allow_blank=True)
    release_year = serializers.IntegerField(allow_null=True)
    genres = serializers.ListField(child=serializers.CharField())
    poster_url = serializers.CharField(allow_blank=True)
    is_featured = serializers.BooleanField()
    url = serializers.CharField()


class DiscoveryListSerializer(serializers.Serializer):
    results = DiscoveryItemSerializer(many=True)
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total = serializers.IntegerField()
    pages = serializers.IntegerField()
