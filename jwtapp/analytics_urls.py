from django.urls import path
from .analytics import (
    AdminDashboardStatsView,
    SalesReportView,
    TopProductsView,
    LowStockAlertView,
    RevenueByVendorView,
    OrderStatusSummaryView,
)

urlpatterns = [
    path('dashboard/',      AdminDashboardStatsView.as_view(), name='analytics_dashboard'),
    path('sales/',          SalesReportView.as_view(),         name='analytics_sales'),
    path('top-products/',   TopProductsView.as_view(),         name='analytics_top_products'),
    path('low-stock/',      LowStockAlertView.as_view(),       name='analytics_low_stock'),
    path('vendor-revenue/', RevenueByVendorView.as_view(),     name='analytics_vendor_revenue'),
    path('order-status/',   OrderStatusSummaryView.as_view(),  name='analytics_order_status'),
]
