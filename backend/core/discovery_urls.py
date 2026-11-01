from django.urls import path

from .discovery_views import DiscoveryView, FeaturedContentView, LatestContentView

urlpatterns = [
    path("", DiscoveryView.as_view(), name="discovery"),
    path("featured/", FeaturedContentView.as_view(), name="discovery-featured"),
    path("latest/", LatestContentView.as_view(), name="discovery-latest"),
]
