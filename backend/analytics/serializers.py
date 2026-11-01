from rest_framework import serializers


class DashboardUserSerializer(serializers.Serializer):
    id = serializers.CharField()
    username = serializers.CharField()
    created_at = serializers.CharField()


class DashboardActivitySerializer(serializers.Serializer):
    type = serializers.CharField()
    title = serializers.CharField()
    created_at = serializers.CharField()


class DashboardCountsSerializer(serializers.Serializer):
    users = serializers.IntegerField()
    movies = serializers.IntegerField()
    series = serializers.IntegerField()
    seasons = serializers.IntegerField()
    episodes = serializers.IntegerField()
    media_assets = serializers.IntegerField()
    media_cleanup_pending = serializers.IntegerField()
    reviews = serializers.IntegerField()
    published = serializers.IntegerField()
    drafts = serializers.IntegerField()


class DashboardSerializer(serializers.Serializer):
    counts = DashboardCountsSerializer()
    recent_users = DashboardUserSerializer(many=True)
    recent_content = DashboardActivitySerializer(many=True)
