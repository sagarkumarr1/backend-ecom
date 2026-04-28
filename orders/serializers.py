from rest_framework import serializers
from .models import Order, OrderItem, OrderTracking, ReturnRequest
from jwtapp.models import Address


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model  = OrderItem
        fields = (
            'id', 'product', 'variant', 'product_name',
            'variant_name', 'unit_price', 'quantity', 'total_price'
        )


class OrderTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model  = OrderTracking
        fields = ('id', 'status', 'message', 'location', 'created_at')


class OrderSerializer(serializers.ModelSerializer):
    items    = OrderItemSerializer(many=True, read_only=True)
    tracking = OrderTrackingSerializer(many=True, read_only=True)
    can_cancel = serializers.ReadOnlyField()
    can_refund = serializers.ReadOnlyField()

    class Meta:
        model  = Order
        fields = (
            'id', 'order_id', 'status', 'payment_status',
            'shipping_name', 'shipping_phone',
            'shipping_line1', 'shipping_line2',
            'shipping_city', 'shipping_state',
            'shipping_pincode', 'shipping_country',
            'subtotal', 'discount_amount', 'shipping_charge',
            'total', 'coupon_code', 'notes',
            'can_cancel', 'can_refund',
            'items', 'tracking', 'created_at', 'updated_at'
        )


class PlaceOrderSerializer(serializers.Serializer):
    """Cart se order place karne ke liye."""
    address_id = serializers.UUIDField()
    notes      = serializers.CharField(required=False, allow_blank=True)

    def validate_address_id(self, value):
        from jwtapp.models import Address
        user = self.context['request'].user
        try:
            address = Address.objects.get(pk=value, user=user)
            self.address = address
        except Address.DoesNotExist:
            raise serializers.ValidationError("Address nahi mila.")
        return value


class CancelOrderSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)


class ReturnRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ReturnRequest
        fields = ('id', 'order', 'reason', 'status', 'admin_note', 'created_at')
        read_only_fields = ('id', 'order', 'status', 'admin_note', 'created_at')


class AdminOrderSerializer(serializers.ModelSerializer):
    items    = OrderItemSerializer(many=True, read_only=True)
    tracking = OrderTrackingSerializer(many=True, read_only=True)

    class Meta:
        model  = Order
        fields = (
            'id', 'order_id', 'user', 'status', 'payment_status',
            'shipping_name', 'shipping_city', 'shipping_state',
            'subtotal', 'discount_amount', 'total',
            'items', 'tracking', 'created_at'
        )
