from django.urls import path

from .views import ContentReviewsView, ReviewDetailView

urlpatterns = [
    path("<str:content_type>/<str:content_id>/", ContentReviewsView.as_view(), name="content-reviews"),
    path("<str:content_type>/<str:content_id>/<str:review_id>/", ReviewDetailView.as_view(), name="content-review-detail"),
]
