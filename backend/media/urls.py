from django.urls import path

from .views import AdminContentMediaUploadView, AdminContentMediaView, AdminMediaLibraryView

urlpatterns = [
    path("", AdminMediaLibraryView.as_view(), name="admin-media-library"),
    path("<str:content_type>/<str:content_id>/", AdminContentMediaView.as_view(), name="admin-content-media"),
    path("<str:content_type>/<str:content_id>/<str:role>/", AdminContentMediaUploadView.as_view(), name="admin-content-media-upload"),
]
