from django.urls import path
from .views import (PublicSeriesList, PublicSeriesFeatured, PublicSeriesGenres, PublicSeriesDetail,
    PublicSeasons, PublicSeasonDetail, PublicEpisodes, PublicSpecials, PublicEpisodeDetail)

urlpatterns=[
    path("",PublicSeriesList.as_view(),name="series-list"),
    path("featured/",PublicSeriesFeatured.as_view(),name="series-featured"),
    path("genres/",PublicSeriesGenres.as_view(),name="series-genres"),
    path("<slug:slug>/",PublicSeriesDetail.as_view(),name="series-detail"),
    path("<slug:slug>/seasons/",PublicSeasons.as_view(),name="series-seasons"),
    path("<slug:slug>/seasons/<slug:season_slug>/",PublicSeasonDetail.as_view(),name="series-season-detail"),
    path("<slug:slug>/seasons/<slug:season_slug>/episodes/",PublicEpisodes.as_view(),name="series-episodes"),
    path("<slug:slug>/specials/",PublicSpecials.as_view(),name="series-specials"),
    path("<slug:slug>/episodes/<slug:episode_slug>/",PublicEpisodeDetail.as_view(),name="series-episode-detail"),
]
