from rest_framework import serializers

from accounts.serializers import StrictSerializer


class MediaAssociationSerializer(serializers.Serializer):
    public_id = serializers.CharField()
    resource_type = serializers.CharField()
    secure_url = serializers.URLField()
    format = serializers.CharField(allow_null=True)
    duration = serializers.FloatField(allow_null=True, required=False)
    content_type = serializers.CharField()
    content_id = serializers.CharField()
    role = serializers.CharField()
    uploaded_at = serializers.DateTimeField()
    uploaded_by = serializers.CharField()


class EmbeddedMediaSerializer(serializers.Serializer):
    public_id = serializers.CharField()
    resource_type = serializers.CharField()
    secure_url = serializers.URLField()
    format = serializers.CharField(allow_null=True)
    duration = serializers.FloatField(allow_null=True, required=False)
    uploaded_at = serializers.DateTimeField()


class MediaUploadSerializer(StrictSerializer):
    file = serializers.FileField()


class MediaAssociationsSerializer(serializers.Serializer):
    video = MediaAssociationSerializer(allow_null=True)
    poster = MediaAssociationSerializer(allow_null=True)


class MediaLibraryItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    public_id = serializers.CharField()
    resource_type = serializers.CharField()
    secure_url = serializers.URLField()
    format = serializers.CharField(allow_null=True)
    duration = serializers.FloatField(allow_null=True)
    content_type = serializers.CharField()
    content_id = serializers.CharField()
    role = serializers.CharField()
    uploaded_at = serializers.DateTimeField()
    cleanup_pending = serializers.BooleanField(required=False)
    reason = serializers.CharField(required=False)


class MediaLibraryResponseSerializer(serializers.Serializer):
    results = MediaLibraryItemSerializer(many=True)
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total = serializers.IntegerField()
    pages = serializers.IntegerField()
