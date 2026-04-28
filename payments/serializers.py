from rest_framework import serializers
from .models import Payment, Refund


class PaymentSerializer(serializers.ModelSerializer):
    order_id = serializers.CharField(source='order.order_id', read_only=True)

    class Meta:
        model  = Payment
        fields = (
            'id', 'order_id', 'razorpay_order_id', 'razorpay_payment_id',
            'amount', 'currency', 'status', 'created_at',
        )


class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Refund
        fields = ('id', 'razorpay_refund_id', 'amount', 'reason', 'status', 'created_at')
