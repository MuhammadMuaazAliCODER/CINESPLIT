from django.urls import path

from .views import FavoriteCollectionView, FavoriteDetailView

urlpatterns = [
    path("", FavoriteCollectionView.as_view(), name="favorites"),
    path("<str:content_type>/<str:content_id>/", FavoriteDetailView.as_view(), name="favorite-detail"),
]
