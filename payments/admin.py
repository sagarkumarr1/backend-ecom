from django.contrib import admin
from .models import Payment, Refund

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display  = ('order', 'user', 'amount', 'status', 'razorpay_payment_id', 'created_at')
    list_filter   = ('status', 'currency')
    search_fields = ('order__order_id', 'razorpay_order_id', 'razorpay_payment_id')
    readonly_fields = ('razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature', 'created_at')

@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display  = ('payment', 'amount', 'status', 'created_at')
    list_filter   = ('status',)
    readonly_fields = ('razorpay_refund_id', 'created_at')
