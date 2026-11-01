from django.utils import timezone
from rest_framework import serializers

from accounts.serializers import StrictSerializer
from media.serializers import EmbeddedMediaSerializer


CONTENT_RATINGS = ("G", "PG", "PG-13", "R", "NC-17", "TV-G", "TV-PG", "TV-14", "TV-MA", "NR")
MOVIE_STATUSES = (("draft", "Draft"), ("published", "Published"))


class MovieWriteSerializer(StrictSerializer):
    title = serializers.CharField(max_length=180, trim_whitespace=True)
    slug = serializers.SlugField(max_length=200, required=False, allow_blank=True)
    short_description = serializers.CharField(max_length=280, trim_whitespace=True)
    description = serializers.CharField(max_length=12000, trim_whitespace=True)
    release_year = serializers.IntegerField(min_value=1870, max_value=2100)
    genres = serializers.ListField(child=serializers.CharField(max_length=50, trim_whitespace=True), min_length=1, max_length=12)
    original_language = serializers.CharField(max_length=50, trim_whitespace=True)
    duration_minutes = serializers.IntegerField(min_value=1, max_value=1000)
    content_rating = serializers.ChoiceField(choices=CONTENT_RATINGS)
    cast = serializers.ListField(child=serializers.CharField(max_length=100, trim_whitespace=True), required=False, max_length=40, default=list)
    director = serializers.CharField(max_length=120, trim_whitespace=True)
    production_company = serializers.CharField(max_length=160, trim_whitespace=True)
    country = serializers.CharField(max_length=100, trim_whitespace=True)
    status = serializers.ChoiceField(choices=MOVIE_STATUSES, required=False, default="draft")
    is_featured = serializers.BooleanField(required=False, default=False)
    poster_url = serializers.URLField(max_length=2048, required=False, allow_blank=True, default="")
    backdrop_url = serializers.URLField(max_length=2048, required=False, allow_blank=True, default="")

    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("A title is required.")
        return value

    def validate_original_language(self, value):
        return value.strip().casefold()

    def validate_genres(self, value):
        cleaned = [item.strip().casefold() for item in value if item.strip()]
        if not cleaned:
            raise serializers.ValidationError("Add at least one genre.")
        if len(set(cleaned)) != len(cleaned):
            raise serializers.ValidationError("Genres must not contain duplicates.")
        return cleaned

    def validate_cast(self, value):
        cleaned = [item.strip() for item in value if item.strip()]
        if len({item.casefold() for item in cleaned}) != len(cleaned):
            raise serializers.ValidationError("Cast members must not contain duplicates.")
        return cleaned

    def validate_release_year(self, value):
        if value > timezone.now().year + 10:
            raise serializers.ValidationError("Release year is too far in the future.")
        return value


class MovieListQuerySerializer(StrictSerializer):
    search = serializers.CharField(required=False, max_length=120, allow_blank=True, trim_whitespace=True)
    genre = serializers.CharField(required=False, max_length=50, trim_whitespace=True)
    release_year = serializers.IntegerField(required=False, min_value=1870, max_value=2100)
    language = serializers.CharField(required=False, max_length=50, trim_whitespace=True)
    content_rating = serializers.ChoiceField(required=False, choices=CONTENT_RATINGS)
    status = serializers.ChoiceField(required=False, choices=MOVIE_STATUSES)
    sort = serializers.ChoiceField(required=False, choices=("-release_year", "release_year", "title", "-title", "-created_at", "created_at"), default="-release_year")
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=100, default=20)


class MovieSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    slug = serializers.CharField()
    short_description = serializers.CharField()
    description = serializers.CharField()
    release_year = serializers.IntegerField()
    genres = serializers.ListField(child=serializers.CharField())
    original_language = serializers.CharField()
    duration_minutes = serializers.IntegerField()
    content_rating = serializers.CharField()
    cast = serializers.ListField(child=serializers.CharField())
    director = serializers.CharField()
    production_company = serializers.CharField()
    country = serializers.CharField()
    status = serializers.CharField()
    is_featured = serializers.BooleanField()
    poster_url = serializers.CharField(allow_blank=True)
    backdrop_url = serializers.CharField(allow_blank=True)
    video = EmbeddedMediaSerializer(required=False, allow_null=True)
    poster_media = EmbeddedMediaSerializer(required=False, allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class AdminMovieSerializer(MovieSerializer):
    created_by = serializers.CharField()


class MovieListResponseSerializer(serializers.Serializer):
    results = MovieSerializer(many=True)
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total = serializers.IntegerField()
    pages = serializers.IntegerField()


class AdminMovieListResponseSerializer(serializers.Serializer):
    results = AdminMovieSerializer(many=True)
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total = serializers.IntegerField()
    pages = serializers.IntegerField()


class MovieGenresResponseSerializer(serializers.Serializer):
    genres = serializers.ListField(child=serializers.CharField())


class MovieDeleteSerializer(StrictSerializer):
    confirmation = serializers.CharField(max_length=200)


class ChapterWriteSerializer(StrictSerializer):
    title = serializers.CharField(max_length=180, trim_whitespace=True)
    slug = serializers.SlugField(max_length=190, required=False, allow_blank=True)
    chapter_number = serializers.IntegerField(min_value=1, required=False)
    description = serializers.CharField(max_length=12000, required=False, allow_blank=True, trim_whitespace=True, default="")
    duration = serializers.IntegerField(min_value=1, max_value=1000)
    status = serializers.ChoiceField(choices=MOVIE_STATUSES, required=False, default="draft")
    is_free = serializers.BooleanField(required=False, default=False)

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("A chapter title is required.")
        return value.strip()


class ChapterSerializer(serializers.Serializer):
    id = serializers.CharField()
    movie_id = serializers.CharField()
    title = serializers.CharField()
    slug = serializers.CharField()
    chapter_number = serializers.IntegerField()
    description = serializers.CharField(allow_blank=True)
    duration = serializers.IntegerField()
    status = serializers.CharField()
    is_free = serializers.BooleanField()
    video = EmbeddedMediaSerializer(required=False, allow_null=True)
    poster_media = EmbeddedMediaSerializer(required=False, allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class AdminChapterSerializer(ChapterSerializer):
    created_by = serializers.CharField()


class ChapterReorderSerializer(StrictSerializer):
    chapter_ids = serializers.ListField(child=serializers.CharField(max_length=24), allow_empty=True, max_length=500)
