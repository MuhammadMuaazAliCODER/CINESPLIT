from django.urls import path
from .views import (AdminSeriesCollection,AdminSeriesDetail,AdminSeasons,AdminSeasonDetail,
    AdminSeasonReorder,AdminEpisodes,AdminEpisodeDetail,AdminEpisodeReorder,AdminSpecials,AdminSpecialReorder)

urlpatterns=[
    path("",AdminSeriesCollection.as_view(),name="admin-series-list"),
    path("<str:series_id>/seasons/reorder/",AdminSeasonReorder.as_view(),name="admin-series-season-reorder"),
    path("<str:series_id>/seasons/<str:season_id>/episodes/reorder/",AdminEpisodeReorder.as_view(),name="admin-season-episode-reorder"),
    path("<str:series_id>/seasons/<str:season_id>/episodes/",AdminEpisodes.as_view(),name="admin-season-episodes"),
    path("<str:series_id>/seasons/<str:season_id>/",AdminSeasonDetail.as_view(),name="admin-season-detail"),
    path("<str:series_id>/seasons/",AdminSeasons.as_view(),name="admin-series-seasons"),
    path("<str:series_id>/specials/reorder/",AdminSpecialReorder.as_view(),name="admin-special-reorder"),
    path("<str:series_id>/specials/",AdminSpecials.as_view(),name="admin-specials"),
    path("<str:series_id>/episodes/<str:episode_id>/",AdminEpisodeDetail.as_view(),name="admin-series-episode-detail"),
    path("<str:series_id>/",AdminSeriesDetail.as_view(),name="admin-series-detail"),
]
