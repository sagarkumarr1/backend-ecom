from django.contrib import admin
from .models import Order, OrderItem, OrderTracking, ReturnRequest


class OrderItemInline(admin.TabularInline):
    model       = OrderItem
    extra       = 0
    readonly_fields = ('product_name', 'variant_name', 'unit_price', 'quantity', 'total_price')


class OrderTrackingInline(admin.TabularInline):
    model       = OrderTracking
    extra       = 0
    readonly_fields = ('status', 'message', 'location', 'created_at', 'updated_by')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display    = ('order_id', 'user', 'status', 'payment_status', 'total', 'created_at')
    list_filter     = ('status', 'payment_status')
    search_fields   = ('order_id', 'user__email', 'shipping_name')
    readonly_fields = ('order_id', 'created_at', 'updated_at')
    inlines         = [OrderItemInline, OrderTrackingInline]
    ordering        = ('-created_at',)


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display  = ('order', 'user', 'status', 'created_at')
    list_filter   = ('status',)
    search_fields = ('order__order_id', 'user__email')
