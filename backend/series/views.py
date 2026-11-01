from pymongo.errors import DuplicateKeyError
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.api_serializers import ErrorSerializer
from accounts.permissions import IsAdministrator, IsAuthenticatedUser
from .serializers import (AdminEpisodeSerializer, AdminSeasonSerializer, AdminSeriesListResponseSerializer,
    AdminSeriesSerializer, DeleteResultSerializer, EpisodeSerializer, EpisodeWriteSerializer,
    GenresResponseSerializer, PublicSeriesQuerySerializer, ReorderSerializer, SeasonSerializer,
    SeasonWriteSerializer, SeriesDeleteSerializer, SeriesListResponseSerializer, SeriesQuerySerializer,
    SeriesSerializer, SeriesWriteSerializer)
from .services import (ContentConflict, InvalidIdValue, SeriesNotFound, admin_episodes, admin_seasons,
    create_episode, create_season, create_series, delete_episode, delete_season, delete_series,
    get_series, list_series, parse_id, public_episode, public_episodes, reorder_episodes,
    reorder_seasons, seasons_for, season_detail, update_episode, update_season, update_series, delete_series_confirmed, get_admin_episode, get_admin_season)


def error(code, detail, code_status, errors=None):
    body={"code":code,"detail":detail}
    if errors is not None:body["errors"]=errors
    return Response(body,status=code_status)


def validated(serializer_class, data, message):
    s=serializer_class(data=data)
    return (s.validated_data,None) if s.is_valid() else (None,error("validation_error",message,status.HTTP_400_BAD_REQUEST,s.errors))


def _series_id_error(value):
    try:parse_id(value)
    except InvalidIdValue:return error("invalid_id","Series id is invalid.",status.HTTP_400_BAD_REQUEST)
    return None


def _handle(exc, item="content"):
    if isinstance(exc,InvalidIdValue):return error("invalid_id",f"{item.title()} id is invalid.",400)
    if isinstance(exc,SeriesNotFound):return error("not_found",f"{item.title()} or its parent was not found.",404)
    return error("content_conflict",str(exc),409)


class PublicSeriesList(APIView):
    permission_classes=[AllowAny];authentication_classes=[]
    @extend_schema(operation_id="series_catalog_list", summary="Browse published series", parameters=[PublicSeriesQuerySerializer], responses={200:SeriesListResponseSerializer,400:ErrorSerializer})
    def get(self,request):
        params,e=validated(PublicSeriesQuerySerializer,request.query_params,"Series query is invalid.")
        if e:return e
        return Response(list_series(params,published=True))


class PublicSeriesFeatured(PublicSeriesList):
    @extend_schema(operation_id="series_featured_list", summary="Browse featured published series", responses={200:SeriesListResponseSerializer})
    def get(self,request):return Response(list_series({},published=True,featured=True))


class PublicSeriesGenres(APIView):
    permission_classes=[AllowAny];authentication_classes=[]
    @extend_schema(operation_id="series_genres_list", summary="List genres of published series", responses={200:GenresResponseSerializer})
    def get(self,request):return Response({"genres":sorted(get_series_genres(),key=str.casefold)})


def get_series_genres():
    from .mongo import get_series_collection
    return [x for x in get_series_collection().distinct("genres",{"status":"published"}) if isinstance(x,str)]


class PublicSeriesDetail(APIView):
    permission_classes=[AllowAny];authentication_classes=[]
    @extend_schema(operation_id="series_public_retrieve", summary="Get a published series", responses={200:SeriesSerializer,404:ErrorSerializer})
    def get(self,request,slug):
        item=get_series(slug,published=True)
        return Response(item) if item else error("not_found","Series not found.",404)


class PublicSeasons(APIView):
    permission_classes=[AllowAny];authentication_classes=[]
    @extend_schema(operation_id="series_seasons_list", summary="List published seasons for a published series", responses={200:SeasonSerializer(many=True),404:ErrorSerializer})
    def get(self,request,slug):
        result=seasons_for(slug)
        return Response(result) if result is not None else error("not_found","Series not found.",404)


class PublicSeasonDetail(APIView):
    permission_classes=[AllowAny];authentication_classes=[]
    @extend_schema(operation_id="series_seasons_public_retrieve", summary="Get a published season", responses={200:SeasonSerializer,404:ErrorSerializer})
    def get(self,request,slug,season_slug):
        result=season_detail(slug,season_slug)
        return Response(result) if result else error("not_found","Season not found.",404)


class PublicEpisodes(APIView):
    permission_classes=[AllowAny];authentication_classes=[]
    @extend_schema(operation_id="series_season_episodes_list", summary="List published regular episodes in a published season", responses={200:EpisodeSerializer(many=True),404:ErrorSerializer})
    def get(self,request,slug,season_slug):
        result=public_episodes(slug,season_slug)
        return Response(EpisodeSerializer(result,many=True).data) if result is not None else error("not_found","Season not found.",404)


class PublicSpecials(APIView):
    permission_classes=[AllowAny];authentication_classes=[]
    @extend_schema(operation_id="series_specials_list", summary="List published specials for a published series", responses={200:EpisodeSerializer(many=True),404:ErrorSerializer})
    def get(self,request,slug):
        result=public_episodes(slug,specials=True)
        return Response(EpisodeSerializer(result,many=True).data) if result is not None else error("not_found","Series not found.",404)


class PublicEpisodeDetail(APIView):
    permission_classes=[AllowAny];authentication_classes=[]
    @extend_schema(operation_id="series_episode_public_retrieve", summary="Get a published episode or special", responses={200:EpisodeSerializer,404:ErrorSerializer})
    def get(self,request,slug,episode_slug):
        result=public_episode(slug,episode_slug)
        return Response(EpisodeSerializer(result).data) if result else error("not_found","Episode not found.",404)


class AdminSeriesCollection(APIView):
    permission_classes=[IsAuthenticatedUser,IsAdministrator]
    @extend_schema(operation_id="admin_series_list", summary="List series for administrators", parameters=[SeriesQuerySerializer], responses={200:AdminSeriesListResponseSerializer,400:ErrorSerializer,403:ErrorSerializer})
    def get(self,request):
        params,e=validated(SeriesQuerySerializer,request.query_params,"Series query is invalid.")
        return e or Response(list_series(params))
    @extend_schema(operation_id="admin_series_create", summary="Create a series", request=SeriesWriteSerializer, responses={201:AdminSeriesSerializer,400:ErrorSerializer,403:ErrorSerializer,409:ErrorSerializer})
    def post(self,request):
        values,e=validated(SeriesWriteSerializer,request.data,"Series data is invalid.")
        if e:return e
        try:return Response(create_series(values,request.user.id),status=201)
        except (ContentConflict,DuplicateKeyError) as exc:return _handle(ContentConflict(str(exc)))


class AdminSeriesDetail(APIView):
    permission_classes=[IsAuthenticatedUser,IsAdministrator]
    @extend_schema(operation_id="admin_series_retrieve", summary="Get a series for administrators", responses={200:AdminSeriesSerializer,400:ErrorSerializer,403:ErrorSerializer,404:ErrorSerializer})
    def get(self,request,series_id):
        err=_series_id_error(series_id)
        if err:return err
        item=get_series(series_id,by_id=True)
        return Response(item) if item else error("not_found","Series not found.",404)
    @extend_schema(operation_id="admin_series_replace", request=SeriesWriteSerializer, responses={200:AdminSeriesSerializer,400:ErrorSerializer,403:ErrorSerializer,404:ErrorSerializer,409:ErrorSerializer})
    def put(self,request,series_id):return self._update(request,series_id,False)
    @extend_schema(operation_id="admin_series_update", request=SeriesWriteSerializer, responses={200:AdminSeriesSerializer,400:ErrorSerializer,403:ErrorSerializer,404:ErrorSerializer,409:ErrorSerializer})
    def patch(self,request,series_id):return self._update(request,series_id,True)
    def _update(self,request,series_id,partial):
        err=_series_id_error(series_id)
        if err:return err
        values,e=validated(SeriesWriteSerializer,request.data,"Series data is invalid.") if not partial else (None,None)
        if partial:
            s=SeriesWriteSerializer(data=request.data,partial=True); e=None if s.is_valid() else error("validation_error","Series data is invalid.",400,s.errors); values=s.validated_data
        if e:return e
        try:return Response(update_series(series_id,values))
        except (InvalidIdValue,SeriesNotFound,ContentConflict) as exc:return _handle(exc,"series")
    @extend_schema(operation_id="admin_series_delete", request=SeriesDeleteSerializer, responses={204:None,400:ErrorSerializer,403:ErrorSerializer,404:ErrorSerializer})
    def delete(self,request,series_id):
        err=_series_id_error(series_id)
        if err:return err
        values,e=validated(SeriesDeleteSerializer,request.data,"Provide the series slug to confirm deletion.")
        if e:return e
        try:
            deleted=delete_series_confirmed(series_id,values["confirmation"])
            return Response(status=204) if deleted else error("deletion_not_confirmed","The confirmation must match the series slug.",400)
        except (InvalidIdValue,SeriesNotFound,ContentConflict) as exc:return _handle(exc,"series")


class AdminSeasons(APIView):
    permission_classes=[IsAuthenticatedUser,IsAdministrator]
    @extend_schema(operation_id="admin_series_seasons_list", responses={200:AdminSeasonSerializer(many=True),400:ErrorSerializer,403:ErrorSerializer,404:ErrorSerializer})
    def get(self,request,series_id):
        err=_series_id_error(series_id)
        if err:return err
        try:return Response(admin_seasons(series_id))
        except (InvalidIdValue,SeriesNotFound) as exc:return _handle(exc,"series")
    @extend_schema(operation_id="admin_series_seasons_create", request=SeasonWriteSerializer, responses={201:AdminSeasonSerializer,400:ErrorSerializer,403:ErrorSerializer,404:ErrorSerializer,409:ErrorSerializer})
    def post(self,request,series_id):
        err=_series_id_error(series_id)
        if err:return err
        values,e=validated(SeasonWriteSerializer,request.data,"Season data is invalid.")
        if e:return e
        try:return Response(create_season(series_id,values,request.user.id),status=201)
        except (InvalidIdValue,SeriesNotFound,ContentConflict,DuplicateKeyError) as exc:return _handle(exc,"season")


class AdminSeasonDetail(APIView):
    permission_classes=[IsAuthenticatedUser,IsAdministrator]
    @extend_schema(operation_id="admin_series_season_retrieve", responses={200:AdminSeasonSerializer,400:ErrorSerializer,403:ErrorSerializer,404:ErrorSerializer})
    def get(self,request,series_id,season_id):
        try:
            item=get_admin_season(series_id,season_id)
            return Response(item) if item else error("not_found","Season not found.",404)
        except (InvalidIdValue,SeriesNotFound) as exc:return _handle(exc,"season")
    @extend_schema(operation_id="admin_series_season_update", request=SeasonWriteSerializer, responses={200:AdminSeasonSerializer,400:ErrorSerializer,403:ErrorSerializer,404:ErrorSerializer,409:ErrorSerializer})
    def patch(self,request,series_id,season_id):
        s=SeasonWriteSerializer(data=request.data,partial=True)
        if not s.is_valid():return error("validation_error","Season data is invalid.",400,s.errors)
        try:return Response(update_season(series_id,season_id,s.validated_data))
        except (InvalidIdValue,SeriesNotFound,ContentConflict,DuplicateKeyError) as exc:return _handle(exc,"season")
    @extend_schema(operation_id="admin_series_season_replace", request=SeasonWriteSerializer, responses={200:AdminSeasonSerializer,400:ErrorSerializer,403:ErrorSerializer,404:ErrorSerializer,409:ErrorSerializer})
    def put(self,request,series_id,season_id):return self.patch(request,series_id,season_id)
    @extend_schema(operation_id="admin_series_season_delete", responses={200:DeleteResultSerializer,400:ErrorSerializer,403:ErrorSerializer,404:ErrorSerializer})
    def delete(self,request,series_id,season_id):
        try:return Response(delete_season(series_id,season_id))
        except (InvalidIdValue,SeriesNotFound,ContentConflict) as exc:return _handle(exc,"season")


class AdminSeasonReorder(APIView):
    permission_classes=[IsAuthenticatedUser,IsAdministrator]
    @extend_schema(operation_id="admin_series_seasons_reorder", request=ReorderSerializer, responses={200:AdminSeasonSerializer(many=True),400:ErrorSerializer,403:ErrorSerializer,404:ErrorSerializer,409:ErrorSerializer})
    def post(self,request,series_id):
        s=ReorderSerializer(data=request.data)
        if not s.is_valid():return error("validation_error","Reorder data is invalid.",400,s.errors)
        try:return Response(reorder_seasons(series_id,s.validated_data["ids"]))
        except (InvalidIdValue,SeriesNotFound,ContentConflict,DuplicateKeyError) as exc:return _handle(exc,"season order")


class AdminEpisodes(APIView):
    permission_classes=[IsAuthenticatedUser,IsAdministrator]
    @extend_schema(operation_id="admin_series_episodes_list", responses={200:AdminEpisodeSerializer(many=True),400:ErrorSerializer,403:ErrorSerializer,404:ErrorSerializer})
    def get(self,request,series_id,season_id=None,special=None):
        try:return Response(AdminEpisodeSerializer(admin_episodes(series_id,season_id,special),many=True).data)
        except (InvalidIdValue,SeriesNotFound) as exc:return _handle(exc,"episode parent")
    @extend_schema(operation_id="admin_series_episodes_create", request=EpisodeWriteSerializer, responses={201:AdminEpisodeSerializer,400:ErrorSerializer,403:ErrorSerializer,404:ErrorSerializer,409:ErrorSerializer})
    def post(self,request,series_id,season_id=None,special=None):
        s=EpisodeWriteSerializer(data=request.data)
        if not s.is_valid():return error("validation_error","Episode data is invalid.",400,s.errors)
        values=s.validated_data
        if season_id and "special_number" in values:return error("validation_error","Regular episodes use episode_number.",400)
        if not season_id and "episode_number" in values:return error("validation_error","Special episodes use special_number.",400)
        try:return Response(AdminEpisodeSerializer(create_episode(series_id,values,request.user.id,season_id)).data,status=201)
        except (InvalidIdValue,SeriesNotFound,ContentConflict,DuplicateKeyError) as exc:return _handle(exc,"episode")


class AdminSpecials(AdminEpisodes):
    @extend_schema(operation_id="admin_series_specials_list", responses={200:AdminEpisodeSerializer(many=True),400:ErrorSerializer,403:ErrorSerializer,404:ErrorSerializer})
    def get(self,request,series_id,season_id=None,special=True):
        return super().get(request,series_id,season_id,special)

    @extend_schema(operation_id="admin_series_specials_create", request=EpisodeWriteSerializer, responses={201:AdminEpisodeSerializer,400:ErrorSerializer,403:ErrorSerializer,404:ErrorSerializer,409:ErrorSerializer})
    def post(self,request,series_id,season_id=None,special=True):
        return super().post(request,series_id,season_id,special)


class AdminEpisodeDetail(APIView):
    permission_classes=[IsAuthenticatedUser,IsAdministrator]
    @extend_schema(operation_id="admin_series_episode_retrieve", responses={200:AdminEpisodeSerializer,400:ErrorSerializer,403:ErrorSerializer,404:ErrorSerializer})
    def get(self,request,series_id,episode_id):
        try:
            item=get_admin_episode(series_id,episode_id)
            return Response(AdminEpisodeSerializer(item).data) if item else error("not_found","Episode not found.",404)
        except (InvalidIdValue,SeriesNotFound) as exc:return _handle(exc,"episode")
    @extend_schema(operation_id="admin_series_episode_update", request=EpisodeWriteSerializer, responses={200:AdminEpisodeSerializer,400:ErrorSerializer,403:ErrorSerializer,404:ErrorSerializer,409:ErrorSerializer})
    def patch(self,request,series_id,episode_id):
        s=EpisodeWriteSerializer(data=request.data,partial=True)
        if not s.is_valid():return error("validation_error","Episode data is invalid.",400,s.errors)
        try:return Response(AdminEpisodeSerializer(update_episode(series_id,episode_id,s.validated_data)).data)
        except (InvalidIdValue,SeriesNotFound,ContentConflict,DuplicateKeyError) as exc:return _handle(exc,"episode")
    @extend_schema(operation_id="admin_series_episode_replace", request=EpisodeWriteSerializer, responses={200:AdminEpisodeSerializer,400:ErrorSerializer,403:ErrorSerializer,404:ErrorSerializer,409:ErrorSerializer})
    def put(self,request,series_id,episode_id):return self.patch(request,series_id,episode_id)
    @extend_schema(operation_id="admin_series_episode_delete", responses={200:DeleteResultSerializer,400:ErrorSerializer,403:ErrorSerializer,404:ErrorSerializer})
    def delete(self,request,series_id,episode_id):
        try:return Response(DeleteResultSerializer(delete_episode(series_id,episode_id)).data)
        except (InvalidIdValue,SeriesNotFound,ContentConflict) as exc:return _handle(exc,"episode")


class AdminEpisodeReorder(APIView):
    permission_classes=[IsAuthenticatedUser,IsAdministrator]
    @extend_schema(operation_id="admin_series_episodes_reorder", request=ReorderSerializer, responses={200:AdminEpisodeSerializer(many=True),400:ErrorSerializer,403:ErrorSerializer,404:ErrorSerializer,409:ErrorSerializer})
    def post(self,request,series_id,season_id=None,special=False):
        s=ReorderSerializer(data=request.data)
        if not s.is_valid():return error("validation_error","Reorder data is invalid.",400,s.errors)
        try:return Response(AdminEpisodeSerializer(reorder_episodes(series_id,s.validated_data["ids"],season_id,special),many=True).data)
        except (InvalidIdValue,SeriesNotFound,ContentConflict,DuplicateKeyError) as exc:return _handle(exc,"episode order")


class AdminSpecialReorder(AdminEpisodeReorder):
    @extend_schema(operation_id="admin_series_specials_reorder", request=ReorderSerializer, responses={200:AdminEpisodeSerializer(many=True),400:ErrorSerializer,403:ErrorSerializer,404:ErrorSerializer,409:ErrorSerializer})
    def post(self,request,series_id,season_id=None,special=True):
        return super().post(request,series_id,season_id,special)
