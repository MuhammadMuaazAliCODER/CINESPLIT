from django.urls import path

from .views import WatchHistoryDetailView, WatchHistoryView

urlpatterns = [
    path("", WatchHistoryView.as_view(), name="watch-history"),
    path("<str:content_type>/<str:content_id>/", WatchHistoryDetailView.as_view(), name="watch-history-detail"),
]
