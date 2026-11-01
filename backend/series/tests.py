from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

from bson import ObjectId
from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory, force_authenticate

from .mongo import ensure_indexes
from .serializers import (AdminEpisodeSerializer, EpisodeWriteSerializer, SeasonWriteSerializer,
    SeriesWriteSerializer)
from .services import (ContentConflict, _data, create_episode, create_series, create_season,
    public_episode, public_episodes, update_episode, update_series)
from .views import (AdminEpisodeDetail, AdminEpisodeReorder, AdminEpisodes, AdminSeasonDetail,
    AdminSeasonReorder, AdminSeasons, AdminSeriesCollection, AdminSeriesDetail, AdminSpecialReorder,
    AdminSpecials, PublicSeasons)


class SeriesSerializerTests(SimpleTestCase):
    def test_series_and_season_fields_validate(self):
        self.assertTrue(SeriesWriteSerializer(data={"title":"North","release_year":2024,"genres":["Drama"]}).is_valid())
        self.assertTrue(SeasonWriteSerializer(data={"title":"Season One","season_number":1}).is_valid())
        self.assertFalse(SeasonWriteSerializer(data={"title":"Season One","season_number":0}).is_valid())

    def test_episode_types_reject_nonpositive_number_and_duration(self):
        self.assertTrue(EpisodeWriteSerializer(data={"title":"Pilot","duration":40}).is_valid())
        self.assertFalse(EpisodeWriteSerializer(data={"title":"Pilot","duration":0,"episode_number":0}).is_valid())

    def test_genres_are_trimmed_casefolded_and_blank_values_are_rejected(self):
        normalized=SeriesWriteSerializer(data={"title":"North","release_year":2024,"genres":[" Drama ","DRAMA","Comedy"]})
        self.assertTrue(normalized.is_valid(),normalized.errors)
        self.assertEqual(normalized.validated_data["genres"],["drama","comedy"])
        for genres in ([],[" "],["", "\t"]):
            invalid=SeriesWriteSerializer(data={"title":"North","release_year":2024,"genres":genres})
            self.assertFalse(invalid.is_valid(),genres)


class SeriesIndexesTests(SimpleTestCase):
    @patch("series.mongo.get_database")
    def test_indexes_enforce_scoped_numbers_and_distinguish_specials(self, get_db):
        db=MagicMock();get_db.return_value=db
        ensure_indexes()
        calls={call.kwargs["name"]:call for call in db.episodes.create_index.call_args_list}
        self.assertTrue(calls["episodes_season_number_unique"].kwargs["unique"])
        self.assertEqual(calls["episodes_season_number_unique"].kwargs["partialFilterExpression"],{"type":"regular"})
        self.assertEqual(calls["episodes_special_number_unique"].kwargs["partialFilterExpression"],{"type":"special"})


class SeriesServiceTests(SimpleTestCase):
    @patch("series.services.get_series_collection")
    def test_create_series_records_creator_and_slug(self,get_collection):
        c=MagicMock();c.find_one.return_value=None;c.insert_one.return_value.inserted_id=ObjectId();get_collection.return_value=c
        result=create_series({"title":"North Road","release_year":2024,"genres":["drama"]},"admin")
        self.assertEqual(result["slug"],"north-road");self.assertEqual(result["created_by"],"admin")

    @patch("series.services.get_series_collection")
    def test_update_series_sets_only_requested_fields_and_maps_slug_conflict(self,get_collection):
        oid=ObjectId();collection=MagicMock();collection.find_one.return_value={"_id":oid,"title":"North","slug":"north"};collection.find_one_and_update.return_value={"_id":oid,"title":"North","slug":"north","is_featured":True};get_collection.return_value=collection
        self.assertTrue(update_series(str(oid),{"is_featured":True})["is_featured"])
        self.assertEqual(collection.find_one_and_update.call_args.args[1]["$set"].keys(),{"is_featured","updated_at"})

    @patch("series.services._parent_transaction")
    @patch("series.services.get_episode_collection")
    @patch("series.services.get_season_collection")
    def test_special_episode_has_null_season_and_series_number(self,get_seasons,get_episodes,parent_transaction):
        series_id=ObjectId();episode_id=ObjectId();episodes=MagicMock();episodes.find.return_value=[];episodes.find_one.return_value=None;episodes.insert_one.return_value.inserted_id=episode_id;get_episodes.return_value=episodes
        def transaction(oid,callback):
            session=object();return callback(session)
        parent_transaction.side_effect=transaction
        result=create_episode(str(series_id),{"title":"Reunion","duration":40},"admin")
        inserted=episodes.insert_one.call_args.args[0]
        self.assertEqual(inserted["type"],"special");self.assertIsNone(inserted["season_id"]);self.assertEqual(inserted["special_number"],1)

    @patch("series.services._parent_transaction")
    @patch("series.services.get_episode_collection")
    @patch("series.services.get_season_collection")
    def test_regular_episode_create_persists_date_as_utc_bson_datetime(self,get_seasons,get_episodes,parent_transaction):
        series_id,season_id,episode_id=ObjectId(),ObjectId(),ObjectId()
        get_seasons.return_value.find_one.return_value={"_id":season_id,"series_id":series_id}
        episodes=get_episodes.return_value;episodes.find.return_value=[];episodes.find_one.return_value=None;episodes.insert_one.return_value.inserted_id=episode_id
        parent_transaction.side_effect=lambda oid,callback:callback(object())
        payload=EpisodeWriteSerializer(data={"title":"Pilot","duration":45,"release_date":"2025-02-03"})
        self.assertTrue(payload.is_valid(),payload.errors)
        created=create_episode(str(series_id),payload.validated_data,"admin",str(season_id))
        inserted=episodes.insert_one.call_args.args[0]
        self.assertEqual(created["type"],"regular")
        self.assertEqual(inserted["episode_number"],1)
        self.assertEqual(inserted["release_date"],datetime(2025,2,3,tzinfo=timezone.utc))

    @patch("series.services._parent_transaction")
    @patch("series.services.get_episode_collection")
    def test_episode_update_supports_date_and_null_and_response_serializes_iso_date(self,get_episodes,parent_transaction):
        oid,series_id=ObjectId(),ObjectId();now=datetime.now(timezone.utc);existing={"_id":oid,"series_id":series_id,"season_id":None,"type":"special","title":"Reunion","slug":"reunion","description":"","duration":40,"status":"draft","is_free":False,"special_number":1,"created_at":now,"updated_at":now,"created_by":"admin"}
        collection=get_episodes.return_value
        updated={**existing,"release_date":datetime(2025,4,5,tzinfo=timezone.utc)}
        collection.find_one.side_effect=[existing,updated]
        parent_transaction.side_effect=lambda parent,callback:callback(object())
        payload=EpisodeWriteSerializer(data={"release_date":"2025-04-05"},partial=True)
        self.assertTrue(payload.is_valid(),payload.errors)
        result=update_episode(str(series_id),str(oid),payload.validated_data)
        self.assertEqual(collection.update_one.call_args.args[1]["$set"]["release_date"],datetime(2025,4,5,tzinfo=timezone.utc))
        result.update(id=str(oid),series_id=str(series_id),season_id=None,created_by="admin")
        serialized=AdminEpisodeSerializer(result).data
        self.assertEqual(serialized["release_date"],"2025-04-05")
        collection.find_one.side_effect=[existing,{**existing,"release_date":None}]
        null_payload=EpisodeWriteSerializer(data={"release_date":None},partial=True)
        self.assertTrue(null_payload.is_valid(),null_payload.errors)
        update_episode(str(series_id),str(oid),null_payload.validated_data)
        self.assertIsNone(collection.update_one.call_args.args[1]["$set"]["release_date"])

    def test_document_conversion_maps_bson_datetime_back_to_date(self):
        oid=ObjectId();item=_data({"_id":oid,"release_date":datetime(2025,1,2,tzinfo=timezone.utc)})
        self.assertEqual(item["release_date"],date(2025,1,2))

    @patch("series.services._parent_transaction")
    @patch("series.services.get_season_collection")
    def test_regular_episode_checks_season_series_relationship(self,get_seasons,parent_transaction):
        series_id,season_id=ObjectId(),ObjectId();get_seasons.return_value.find_one.return_value=None
        parent_transaction.side_effect=lambda oid,callback:callback(object())
        with self.assertRaises(Exception):create_episode(str(series_id),{"title":"Pilot","duration":42},"admin",str(season_id))

    @patch("series.services.get_episode_collection")
    @patch("series.services.get_season_collection")
    @patch("series.services.get_series_collection")
    def test_public_specials_are_series_scoped_and_episode_requires_published_season(self,get_series,get_seasons,get_episodes):
        series_id,season_id=ObjectId(),ObjectId();get_series.return_value.find_one.return_value={"_id":series_id,"slug":"north","status":"published"}
        cursor=MagicMock();cursor.sort.return_value=[];get_episodes.return_value.find.return_value=cursor
        from .services import public_episodes
        public_episodes("north",specials=True)
        self.assertEqual(get_episodes.return_value.find.call_args.args[0],{"series_id":series_id,"type":"special","status":"published"})
        get_episodes.return_value.find_one.return_value={"_id":ObjectId(),"series_id":series_id,"season_id":season_id,"type":"regular","status":"published"}
        get_seasons.return_value.find_one.return_value=None
        self.assertIsNone(public_episode("north","pilot"))


class SeriesViewsTests(SimpleTestCase):
    def test_public_seasons_calls_only_public_service(self):
        request=APIRequestFactory().get("/api/series/north/seasons/")
        with patch("series.views.seasons_for",return_value=[]) as lookup:
            response=PublicSeasons.as_view()(request,slug="north")
        self.assertEqual(response.status_code,200);lookup.assert_called_once_with("north")

    def test_regular_user_is_forbidden_from_series_admin(self):
        request=APIRequestFactory().get("/api/admin/series/")
        force_authenticate(request,user=type("User",(),{"id":"u","role":"user","is_authenticated":True})())
        self.assertEqual(AdminSeriesCollection.as_view()(request).status_code,403)

    def test_regular_user_is_forbidden_from_every_admin_view_family(self):
        user=type("User",(),{"id":"u","role":"user","is_authenticated":True})()
        cases=[(AdminSeriesDetail,{"series_id":str(ObjectId())}),(AdminSeasons,{"series_id":str(ObjectId())}),
            (AdminSeasonDetail,{"series_id":str(ObjectId()),"season_id":str(ObjectId())}),
            (AdminSeasonReorder,{"series_id":str(ObjectId())}),(AdminEpisodes,{"series_id":str(ObjectId()),"season_id":str(ObjectId())}),
            (AdminSpecials,{"series_id":str(ObjectId())}),(AdminEpisodeDetail,{"series_id":str(ObjectId()),"episode_id":str(ObjectId())}),
            (AdminEpisodeReorder,{"series_id":str(ObjectId()),"season_id":str(ObjectId())}),
            (AdminSpecialReorder,{"series_id":str(ObjectId())})]
        for view,kwargs in cases:
            request=APIRequestFactory().get("/api/admin/series/")
            force_authenticate(request,user=user)
            with self.subTest(view=view.__name__):self.assertEqual(view.as_view()(request,**kwargs).status_code,403)

    def test_routes_are_registered(self):
        self.assertEqual(reverse("series-list"),"/api/series/")
        self.assertEqual(reverse("series-specials",kwargs={"slug":"north"}),"/api/series/north/specials/")
        self.assertEqual(reverse("admin-series-seasons",kwargs={"series_id":"65f000000000000000000001"}),"/api/admin/series/65f000000000000000000001/seasons/")

    def test_schema_documents_series_payloads_responses_query_and_unique_operation_ids(self):
        from drf_spectacular.generators import SchemaGenerator
        schema=SchemaGenerator().get_schema(request=None,public=True)
        series_paths={path:item for path,item in schema["paths"].items() if "/series" in path}
        self.assertIn("/api/series/",series_paths)
        self.assertIn("application/json",series_paths["/api/admin/series/"]["post"]["requestBody"]["content"])
        list_schema=series_paths["/api/series/"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
        self.assertIn("SeriesListResponse",list_schema.get("$ref",""))
        self.assertIn("results",schema["components"]["schemas"]["SeriesListResponse"]["properties"])
        public_query={p["name"] for p in series_paths["/api/series/"]["get"]["parameters"]}
        self.assertTrue({"page","page_size","search","genre"}.issubset(public_query))
        operations=[op["operationId"] for item in series_paths.values() for method,op in item.items() if method in {"get","post","put","patch","delete"}]
        self.assertEqual(len(operations),len(set(operations)))
