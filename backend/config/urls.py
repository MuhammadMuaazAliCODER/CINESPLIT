from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", include("core.urls")),
    path("api/discover/", include("core.discovery_urls")),
    path("api/auth/", include("accounts.urls")),
    path("api/favorites/", include("favorites.urls")),
    path("api/watch-history/", include("watch_progress.urls")),
    path("api/reviews/", include("reviews.urls")),
    path("api/admin/analytics/", include("analytics.urls")),
    path("api/movies/", include("movies.urls")),
    path("api/admin/movies/", include("movies.admin_urls")),
    path("api/series/", include("series.urls")),
    path("api/admin/series/", include("series.admin_urls")),
    path("api/admin/media/", include("media.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
