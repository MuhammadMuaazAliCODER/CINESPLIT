from rest_framework import serializers


class MessageSerializer(serializers.Serializer):
    detail = serializers.CharField()


class ErrorSerializer(serializers.Serializer):
    code = serializers.CharField(required=False)
    detail = serializers.CharField(required=False)
    errors = serializers.DictField(required=False)


class UserProfileSerializer(serializers.Serializer):
    id = serializers.CharField()
    username = serializers.CharField()
    email = serializers.EmailField()
    role = serializers.CharField()
    is_active = serializers.BooleanField()
    is_verified = serializers.BooleanField()
    full_name = serializers.CharField(allow_blank=True)
    avatar = serializers.CharField(allow_blank=True)
    bio = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    last_login = serializers.DateTimeField(allow_null=True)


class AccessTokenResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    token_type = serializers.ChoiceField(choices=["Bearer"])
    user = UserProfileSerializer()


class RefreshResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    token_type = serializers.ChoiceField(choices=["Bearer"])


class RegistrationResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    email = serializers.EmailField()
    verification_required = serializers.BooleanField()


class CsrfResponseSerializer(serializers.Serializer):
    csrf_token = serializers.CharField()
