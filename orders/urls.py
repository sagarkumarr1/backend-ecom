from django.urls import path
from .views import (
    PlaceOrderView, OrderListView, OrderDetailView,
    CancelOrderView, OrderTrackingView, ReturnRequestView,
    AdminOrderListView, AdminOrderDetailView,
    AdminUpdateOrderStatusView, AdminReturnListView, AdminReturnActionView,
)

urlpatterns = [

    # ── Customer ──────────────────────────────────────────────────────────
    path('',                                  OrderListView.as_view(),    name='order_list'),
    path('place/',                            PlaceOrderView.as_view(),   name='order_place'),
    path('<str:order_id>/',                   OrderDetailView.as_view(),  name='order_detail'),
    path('<str:order_id>/cancel/',            CancelOrderView.as_view(),  name='order_cancel'),
    path('<str:order_id>/tracking/',          OrderTrackingView.as_view(), name='order_tracking'),
    path('<str:order_id>/return/',            ReturnRequestView.as_view(), name='order_return'),

    # ── Admin ─────────────────────────────────────────────────────────────
    path('admin/',                            AdminOrderListView.as_view(),        name='admin_order_list'),
    path('admin/returns/',                    AdminReturnListView.as_view(),       name='admin_return_list'),
    path('admin/returns/<uuid:pk>/',          AdminReturnActionView.as_view(),     name='admin_return_action'),
    path('admin/<str:order_id>/',             AdminOrderDetailView.as_view(),      name='admin_order_detail'),
    path('admin/<str:order_id>/status/',      AdminUpdateOrderStatusView.as_view(), name='admin_order_status'),
]
