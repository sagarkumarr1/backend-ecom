"""
jwtapp/analytics.py
Day 11-12 — Admin Analytics Dashboard
Sales reports, revenue, top products, low stock alerts.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Avg, Q, F
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from datetime import timedelta

from jwtapp.permissions import IsAdminUser
from orders.models import Order, OrderItem
from products.models import Product, Stock
from jwtapp.models import User
from payments.models import Payment
from reviews.models import Review


class AdminDashboardStatsView(APIView):
    """
    GET /api/admin/analytics/dashboard/
    Overall stats — ek page pe sab kuch.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        now   = timezone.now()
        today = now.date()
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0)

        # Revenue
        total_revenue      = Payment.objects.filter(status='success').aggregate(
            total=Sum('amount'))['total'] or 0
        today_revenue      = Payment.objects.filter(
            status='success', created_at__date=today
        ).aggregate(total=Sum('amount'))['total'] or 0
        month_revenue      = Payment.objects.filter(
            status='success', created_at__gte=this_month_start
        ).aggregate(total=Sum('amount'))['total'] or 0

        # Orders
        total_orders   = Order.objects.count()
        today_orders   = Order.objects.filter(created_at__date=today).count()
        pending_orders = Order.objects.filter(status='pending').count()

        # Users
        total_users    = User.objects.count()
        new_today      = User.objects.filter(date_joined__date=today).count()

        # Products
        total_products  = Product.objects.filter(status='active').count()
        low_stock_count = Stock.objects.filter(
            quantity__lte=models.F('low_stock_threshold')
        ).count()
        out_of_stock    = Stock.objects.filter(quantity=0).count()

        return Response({
            "revenue": {
                "total":       float(total_revenue),
                "today":       float(today_revenue),
                "this_month":  float(month_revenue),
            },
            "orders": {
                "total":   total_orders,
                "today":   today_orders,
                "pending": pending_orders,
            },
            "users": {
                "total":     total_users,
                "new_today": new_today,
            },
            "products": {
                "active":       total_products,
                "low_stock":    low_stock_count,
                "out_of_stock": out_of_stock,
            },
        })


class SalesReportView(APIView):
    """
    GET /api/admin/analytics/sales/?period=daily&days=30
    GET /api/admin/analytics/sales/?period=monthly&months=12
    Revenue chart ke liye data.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        period = request.query_params.get('period', 'daily')
        now    = timezone.now()

        if period == 'daily':
            days   = int(request.query_params.get('days', 30))
            start  = now - timedelta(days=days)
            data   = Payment.objects.filter(
                status='success', created_at__gte=start
            ).annotate(
                date=TruncDate('created_at')
            ).values('date').annotate(
                revenue=Sum('amount'),
                orders=Count('id'),
            ).order_by('date')

        else:  # monthly
            months = int(request.query_params.get('months', 12))
            start  = now - timedelta(days=months * 30)
            data   = Payment.objects.filter(
                status='success', created_at__gte=start
            ).annotate(
                date=TruncMonth('created_at')
            ).values('date').annotate(
                revenue=Sum('amount'),
                orders=Count('id'),
            ).order_by('date')

        return Response({
            "period": period,
            "data": [
                {
                    "date":    str(item['date']),
                    "revenue": float(item['revenue'] or 0),
                    "orders":  item['orders'],
                }
                for item in data
            ]
        })


class TopProductsView(APIView):
    """
    GET /api/admin/analytics/top-products/?limit=10
    Sabse zyada bikne wale products.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        limit   = int(request.query_params.get('limit', 10))
        days    = int(request.query_params.get('days', 30))
        start   = timezone.now() - timedelta(days=days)

        top = OrderItem.objects.filter(
            order__created_at__gte=start,
            order__status__in=['confirmed', 'processing', 'shipped', 'delivered']
        ).values(
            'product__name', 'product__slug'
        ).annotate(
            total_sold=Sum('quantity'),
            revenue=Sum('total_price'),
        ).order_by('-total_sold')[:limit]

        return Response({
            "period_days": days,
            "top_products": list(top),
        })


class LowStockAlertView(APIView):
    """
    GET /api/admin/analytics/low-stock/
    Stock khatam hone wale products — vendor aur admin ko alert.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        low_stock = Stock.objects.filter(
            quantity__lte=F('low_stock_threshold')
        ).select_related('product__vendor', 'product__category')

        data = []
        for s in low_stock:
            data.append({
                "product_name": s.product.name,
                "product_slug": s.product.slug,
                "vendor":       s.product.vendor.email,
                "category":     s.product.category.name if s.product.category else None,
                "quantity":     s.quantity,
                "threshold":    s.low_stock_threshold,
                "status":       "out_of_stock" if s.quantity == 0 else "low_stock",
            })

        return Response({
            "count": len(data),
            "alerts": sorted(data, key=lambda x: x['quantity']),
        })


class RevenueByVendorView(APIView):
    """
    GET /api/admin/analytics/vendor-revenue/
    Vendor-wise revenue breakdown.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        days  = int(request.query_params.get('days', 30))
        start = timezone.now() - timedelta(days=days)

        data = OrderItem.objects.filter(
            order__created_at__gte=start,
            order__status__in=['confirmed', 'processing', 'shipped', 'delivered']
        ).values(
            'product__vendor__email',
            'product__vendor__shop_name',
        ).annotate(
            total_orders=Count('order', distinct=True),
            total_sold=Sum('quantity'),
            revenue=Sum('total_price'),
        ).order_by('-revenue')

        return Response({
            "period_days":    days,
            "vendor_revenue": list(data),
        })


class OrderStatusSummaryView(APIView):
    """
    GET /api/admin/analytics/order-status/
    Status-wise order count — pie chart ke liye.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        summary = Order.objects.values('status').annotate(count=Count('id'))
        return Response({
            "order_status_summary": list(summary),
            "total": Order.objects.count(),
        })
