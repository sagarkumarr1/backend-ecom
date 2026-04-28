from django.urls import path
from .views import (
    ProductReviewListView, MyReviewsView,
    ReviewDetailView, ReviewVoteView,
    AdminReviewListView, AdminReviewActionView,
)

urlpatterns = [
    path('my/',                       MyReviewsView.as_view(),         name='my_reviews'),
    path('admin/',                    AdminReviewListView.as_view(),    name='admin_review_list'),
    path('admin/<uuid:pk>/',          AdminReviewActionView.as_view(),  name='admin_review_action'),
    path('<slug:slug>/',              ProductReviewListView.as_view(),  name='product_reviews'),
    path('<uuid:pk>/update/',         ReviewDetailView.as_view(),       name='review_update'),
    path('<uuid:pk>/vote/',           ReviewVoteView.as_view(),         name='review_vote'),
]
