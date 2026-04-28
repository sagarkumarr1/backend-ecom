from rest_framework import serializers
from .models import Cart, CartItem, WishlistItem, Coupon
from products.serializers import ProductListSerializer, ProductVariantSerializer


# ─── Coupon ───────────────────────────────────────────────────────────────
class CouponSerializer(serializers.ModelSerializer):
    is_valid = serializers.ReadOnlyField()

    class Meta:
        model  = Coupon
        fields = (
            'id', 'code', 'description', 'discount_type',
            'discount_value', 'min_order_amount', 'max_discount',
            'is_valid', 'valid_until',
        )


# ─── Cart Item ────────────────────────────────────────────────────────────
class CartItemSerializer(serializers.ModelSerializer):
    product     = ProductListSerializer(read_only=True)
    product_id  = serializers.UUIDField(write_only=True)
    variant_id  = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    variant     = ProductVariantSerializer(read_only=True)
    unit_price  = serializers.ReadOnlyField()
    total_price = serializers.ReadOnlyField()
    available_stock = serializers.ReadOnlyField()

    class Meta:
        model  = CartItem
        fields = (
            'id', 'product', 'product_id', 'variant', 'variant_id',
            'quantity', 'unit_price', 'total_price', 'available_stock', 'added_at',
        )
        read_only_fields = ('id', 'added_at')

    def validate(self, attrs):
        from products.models import Product, ProductVariant

        # Product exist karta hai?
        try:
            product = Product.objects.get(pk=attrs['product_id'], status='active')
        except Product.DoesNotExist:
            raise serializers.ValidationError({"product_id": "Product nahi mila ya active nahi hai."})

        attrs['product'] = product

        # Variant check
        variant_id = attrs.get('variant_id')
        if variant_id:
            try:
                variant = ProductVariant.objects.get(pk=variant_id, product=product, is_active=True)
                attrs['variant'] = variant
            except ProductVariant.DoesNotExist:
                raise serializers.ValidationError({"variant_id": "Variant nahi mila."})
        else:
            attrs['variant'] = None

        # Stock check
        quantity = attrs.get('quantity', 1)
        variant  = attrs.get('variant')
        if variant:
            if variant.stock < quantity:
                raise serializers.ValidationError(
                    {"quantity": f"Sirf {variant.stock} units available hain."}
                )
        else:
            try:
                stock = product.stock.quantity
                if stock < quantity:
                    raise serializers.ValidationError(
                        {"quantity": f"Sirf {stock} units available hain."}
                    )
            except Exception:
                pass

        return attrs


# ─── Cart ─────────────────────────────────────────────────────────────────
class CartSerializer(serializers.ModelSerializer):
    items          = CartItemSerializer(many=True, read_only=True)
    coupon         = CouponSerializer(read_only=True)
    subtotal       = serializers.ReadOnlyField()
    discount_amount = serializers.ReadOnlyField()
    total          = serializers.ReadOnlyField()
    total_items    = serializers.ReadOnlyField()

    class Meta:
        model  = Cart
        fields = (
            'id', 'items', 'coupon',
            'subtotal', 'discount_amount', 'total', 'total_items',
            'updated_at',
        )


# ─── Coupon Apply ─────────────────────────────────────────────────────────
class ApplyCouponSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)

    def validate_code(self, value):
        try:
            coupon = Coupon.objects.get(code__iexact=value)
        except Coupon.DoesNotExist:
            raise serializers.ValidationError("Coupon code invalid hai.")

        if not coupon.is_valid:
            raise serializers.ValidationError("Coupon expire ho gaya hai ya limit khatam ho gayi.")

        self.coupon = coupon
        return value


# ─── Wishlist ─────────────────────────────────────────────────────────────
class WishlistItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)

    class Meta:
        model  = WishlistItem
        fields = ('id', 'product', 'added_at')
        read_only_fields = ('id', 'added_at')
