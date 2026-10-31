import re

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from rest_framework import serializers


USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_.]{3,30}$")


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if hasattr(data, "keys"):
            unknown = set(data.keys()) - set(self.fields.keys())
            if unknown:
                raise serializers.ValidationError({key: "Unknown field." for key in sorted(unknown)})
        return super().to_internal_value(data)


def normalize_email(value):
    email = value.strip().casefold()
    try:
        validate_email(email)
    except DjangoValidationError as exc:
        raise serializers.ValidationError("Enter a valid email address.") from exc
    return email


def validate_password_strength(value):
    if len(value) < 12:
        raise serializers.ValidationError("Use at least 12 characters.")
    if len(value.encode("utf-8")) > 72:
        raise serializers.ValidationError("Password must be no more than 72 UTF-8 bytes.")
    categories = sum((any(char.islower() for char in value), any(char.isupper() for char in value),
                      any(char.isdigit() for char in value), any(not char.isalnum() for char in value)))
    if categories < 3:
        raise serializers.ValidationError("Include at least three of: lowercase, uppercase, numbers, and symbols.")
    return value


class RegistrationSerializer(StrictSerializer):
    username = serializers.CharField(min_length=3, max_length=30, trim_whitespace=True)
    email = serializers.CharField(max_length=254, trim_whitespace=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False, validators=[validate_password_strength])
    password_confirmation = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_username(self, value):
        username = value.strip().casefold()
        if not USERNAME_PATTERN.fullmatch(username):
            raise serializers.ValidationError("Use 3–30 letters, numbers, dots, or underscores.")
        return username

    def validate_email(self, value):
        return normalize_email(value)

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirmation"]:
            raise serializers.ValidationError({"password_confirmation": "Passwords do not match."})
        return attrs


class EmailCodeSerializer(StrictSerializer):
    email = serializers.CharField(max_length=254, trim_whitespace=True)
    code = serializers.RegexField(r"^\d{6}$", max_length=6, min_length=6)

    def validate_email(self, value):
        return normalize_email(value)


class EmailSerializer(StrictSerializer):
    email = serializers.CharField(max_length=254, trim_whitespace=True)

    def validate_email(self, value):
        return normalize_email(value)


class LoginSerializer(StrictSerializer):
    email = serializers.CharField(max_length=254, trim_whitespace=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, value):
        return normalize_email(value)


class ProfileSerializer(StrictSerializer):
    username = serializers.CharField(min_length=3, max_length=30, required=False, trim_whitespace=True)
    full_name = serializers.CharField(max_length=120, required=False, allow_blank=True, trim_whitespace=True)
    avatar = serializers.URLField(max_length=2048, required=False, allow_blank=True)
    bio = serializers.CharField(max_length=500, required=False, allow_blank=True, trim_whitespace=True)

    def validate_username(self, value):
        username = value.strip().casefold()
        if not USERNAME_PATTERN.fullmatch(username):
            raise serializers.ValidationError("Use 3–30 letters, numbers, dots, or underscores.")
        return username


class ChangePasswordSerializer(StrictSerializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False, validators=[validate_password_strength])
    password_confirmation = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["password_confirmation"]:
            raise serializers.ValidationError({"password_confirmation": "Passwords do not match."})
        return attrs
