from rest_framework import serializers
from accounts.serializers import StrictSerializer
from media.serializers import EmbeddedMediaSerializer

STATUSES = (("draft", "Draft"), ("published", "Published"))


class SeriesWriteSerializer(StrictSerializer):
    title=serializers.CharField(max_length=180)
    slug=serializers.SlugField(max_length=190,required=False,allow_blank=True)
    short_description=serializers.CharField(max_length=280,required=False,allow_blank=True,default="")
    description=serializers.CharField(max_length=12000,required=False,allow_blank=True,default="")
    release_year=serializers.IntegerField(min_value=1870,max_value=2100)
    genres=serializers.ListField(child=serializers.CharField(max_length=50,trim_whitespace=True),min_length=1,max_length=12)
    language=serializers.CharField(max_length=50,required=False,allow_blank=True,default="")
    content_rating=serializers.CharField(max_length=20,required=False,allow_blank=True,default="NR")
    cast=serializers.ListField(child=serializers.CharField(max_length=100),required=False,default=list)
    director=serializers.CharField(max_length=120,required=False,allow_blank=True,default="")
    production_company=serializers.CharField(max_length=160,required=False,allow_blank=True,default="")
    country=serializers.CharField(max_length=100,required=False,allow_blank=True,default="")
    status=serializers.ChoiceField(choices=STATUSES,required=False,default="draft")
    is_featured=serializers.BooleanField(required=False,default=False)
    poster_url=serializers.URLField(max_length=2048,required=False,allow_blank=True,default="")
    backdrop_url=serializers.URLField(max_length=2048,required=False,allow_blank=True,default="")
    def validate_genres(self,v):
        normalized=list(dict.fromkeys(x.strip().casefold() for x in v if x.strip()))
        if not normalized:
            raise serializers.ValidationError("Add at least one nonblank genre.")
        return normalized


class SeasonWriteSerializer(StrictSerializer):
    title=serializers.CharField(max_length=180)
    slug=serializers.SlugField(max_length=190,required=False,allow_blank=True)
    season_number=serializers.IntegerField(min_value=1,required=False)
    description=serializers.CharField(max_length=12000,required=False,allow_blank=True,default="")
    release_year=serializers.IntegerField(min_value=1870,max_value=2100,required=False,allow_null=True)
    status=serializers.ChoiceField(choices=STATUSES,required=False,default="draft")


class EpisodeWriteSerializer(StrictSerializer):
    title=serializers.CharField(max_length=180)
    slug=serializers.SlugField(max_length=190,required=False,allow_blank=True)
    episode_number=serializers.IntegerField(min_value=1,required=False)
    special_number=serializers.IntegerField(min_value=1,required=False)
    description=serializers.CharField(max_length=12000,required=False,allow_blank=True,default="")
    duration=serializers.IntegerField(min_value=1,max_value=1000)
    status=serializers.ChoiceField(choices=STATUSES,required=False,default="draft")
    is_free=serializers.BooleanField(required=False,default=False)
    release_date=serializers.DateField(required=False,allow_null=True)


class ReorderSerializer(StrictSerializer):
    ids=serializers.ListField(child=serializers.CharField(max_length=24),allow_empty=True,max_length=500)

class SeriesDeleteSerializer(StrictSerializer):
    confirmation=serializers.CharField(max_length=190)


class SeriesQuerySerializer(StrictSerializer):
    search=serializers.CharField(required=False,max_length=120,allow_blank=True)
    genre=serializers.CharField(required=False,max_length=50,allow_blank=True)
    release_year=serializers.IntegerField(required=False,min_value=1870,max_value=2100)
    status=serializers.ChoiceField(required=False,choices=STATUSES)
    page=serializers.IntegerField(required=False,min_value=1,default=1)
    page_size=serializers.IntegerField(required=False,min_value=1,max_value=100,default=20)
    sort=serializers.ChoiceField(required=False,choices=("-release_year","release_year","title","-created_at"),default="-release_year")


class PublicSeriesQuerySerializer(StrictSerializer):
    search=serializers.CharField(required=False,max_length=120,allow_blank=True)
    genre=serializers.CharField(required=False,max_length=50,allow_blank=True)
    release_year=serializers.IntegerField(required=False,min_value=1870,max_value=2100)
    page=serializers.IntegerField(required=False,min_value=1,default=1)
    page_size=serializers.IntegerField(required=False,min_value=1,max_value=100,default=20)
    sort=serializers.ChoiceField(required=False,choices=("-release_year","release_year","title","-created_at"),default="-release_year")


class SeriesSerializer(serializers.Serializer):
    id=serializers.CharField()
    title=serializers.CharField()
    slug=serializers.CharField()
    short_description=serializers.CharField(allow_blank=True)
    description=serializers.CharField(allow_blank=True)
    release_year=serializers.IntegerField()
    genres=serializers.ListField(child=serializers.CharField())
    language=serializers.CharField(allow_blank=True)
    content_rating=serializers.CharField(allow_blank=True)
    cast=serializers.ListField(child=serializers.CharField())
    director=serializers.CharField(allow_blank=True)
    production_company=serializers.CharField(allow_blank=True)
    country=serializers.CharField(allow_blank=True)
    status=serializers.CharField()
    is_featured=serializers.BooleanField()
    poster_url=serializers.CharField(allow_blank=True)
    backdrop_url=serializers.CharField(allow_blank=True)
    created_at=serializers.DateTimeField()
    updated_at=serializers.DateTimeField()


class AdminSeriesSerializer(SeriesSerializer):
    created_by=serializers.CharField()


class SeriesListResponseSerializer(serializers.Serializer):
    results=SeriesSerializer(many=True)
    page=serializers.IntegerField()
    page_size=serializers.IntegerField()
    total=serializers.IntegerField()
    pages=serializers.IntegerField()


class AdminSeriesListResponseSerializer(SeriesListResponseSerializer):
    results=AdminSeriesSerializer(many=True)


class GenresResponseSerializer(serializers.Serializer):
    genres=serializers.ListField(child=serializers.CharField())


class DeleteResultSerializer(serializers.Serializer):
    deleted=serializers.BooleanField()
    renumbered=serializers.BooleanField()


class SeasonSerializer(serializers.Serializer):
    id=serializers.CharField()
    series_id=serializers.CharField()
    title=serializers.CharField()
    season_number=serializers.IntegerField()
    slug=serializers.CharField()
    description=serializers.CharField(allow_blank=True)
    release_year=serializers.IntegerField(allow_null=True)
    status=serializers.CharField()
    created_at=serializers.DateTimeField()
    updated_at=serializers.DateTimeField()


class AdminSeasonSerializer(SeasonSerializer):
    created_by=serializers.CharField()


class EpisodeSerializer(serializers.Serializer):
    id=serializers.CharField()
    series_id=serializers.CharField()
    season_id=serializers.CharField(allow_null=True)
    type=serializers.ChoiceField(choices=("regular","special"))
    title=serializers.CharField()
    slug=serializers.CharField()
    episode_number=serializers.IntegerField(required=False)
    special_number=serializers.IntegerField(required=False)
    description=serializers.CharField(allow_blank=True)
    duration=serializers.IntegerField()
    status=serializers.CharField()
    is_free=serializers.BooleanField()
    release_date=serializers.DateField(allow_null=True,required=False)
    video=EmbeddedMediaSerializer(required=False,allow_null=True)
    poster_media=EmbeddedMediaSerializer(required=False,allow_null=True)
    created_at=serializers.DateTimeField()
    updated_at=serializers.DateTimeField()


class AdminEpisodeSerializer(EpisodeSerializer):
    created_by=serializers.CharField()
