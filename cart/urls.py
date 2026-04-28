from django.urls import path
from .views import (
    CartView, CartItemAddView, CartItemUpdateView,
    ApplyCouponView, RemoveCouponView, CartSummaryView,
    WishlistView, WishlistItemDeleteView, WishlistMoveToCartView,
    AdminCouponListCreateView, AdminCouponDetailView,
)

urlpatterns = [

    # ── Cart ─────────────────────────────────────────────────────────────
    path('',                    CartView.as_view(),          name='cart'),
    path('summary/',            CartSummaryView.as_view(),   name='cart_summary'),
    path('items/',              CartItemAddView.as_view(),   name='cart_item_add'),
    path('items/<uuid:pk>/',    CartItemUpdateView.as_view(), name='cart_item_update'),

    # ── Coupon ───────────────────────────────────────────────────────────
    path('coupon/apply/',       ApplyCouponView.as_view(),   name='coupon_apply'),
    path('coupon/remove/',      RemoveCouponView.as_view(),  name='coupon_remove'),

    # ── Wishlist ─────────────────────────────────────────────────────────
    path('wishlist/',                           WishlistView.as_view(),           name='wishlist'),
    path('wishlist/<uuid:pk>/',                 WishlistItemDeleteView.as_view(), name='wishlist_delete'),
    path('wishlist/<uuid:pk>/move-to-cart/',    WishlistMoveToCartView.as_view(), name='wishlist_move_to_cart'),

    # ── Admin — Coupons ───────────────────────────────────────────────────
    path('admin/coupons/',          AdminCouponListCreateView.as_view(), name='admin_coupon_list'),
    path('admin/coupons/<uuid:pk>/', AdminCouponDetailView.as_view(),   name='admin_coupon_detail'),
]
