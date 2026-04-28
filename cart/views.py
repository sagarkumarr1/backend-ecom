from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import Cart, CartItem, WishlistItem, Coupon
from .serializers import (
    CartSerializer, CartItemSerializer,
    ApplyCouponSerializer, WishlistItemSerializer, CouponSerializer
)
from products.models import Product
from jwtapp.permissions import IsAdminUser


# ══════════════════════════════════════════════════════════════
# CART VIEWS
# ══════════════════════════════════════════════════════════════

class CartView(APIView):
    """
    GET  /api/cart/   — apna cart dekho (auto-create hoga)
    DELETE /api/cart/ — cart clear karo
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.prefetch_related(
            'items__product__images',
            'items__variant',
        ).get_or_create(user=request.user)
        return Response(CartSerializer(cart).data)

    def delete(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart.items.all().delete()
        cart.coupon = None
        cart.save()
        return Response({"message": "Cart clear ho gaya."})


class CartItemAddView(APIView):
    """
    POST /api/cart/items/
    Body: {"product_id": "uuid", "variant_id": "uuid", "quantity": 2}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart, _ = Cart.objects.get_or_create(user=request.user)

        product = serializer.validated_data['product']
        variant = serializer.validated_data.get('variant')
        quantity = serializer.validated_data['quantity']

        # Already cart mein hai toh quantity add karo
        existing = CartItem.objects.filter(
            cart=cart, product=product, variant=variant
        ).first()

        if existing:
            new_qty = existing.quantity + quantity
            # Stock check
            available = existing.available_stock
            if available and new_qty > available:
                return Response(
                    {"error": f"Sirf {available} units available hain."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            existing.quantity = new_qty
            existing.save()
            item = existing
        else:
            item = CartItem.objects.create(
                cart=cart, product=product,
                variant=variant, quantity=quantity
            )

        return Response(CartItemSerializer(item).data, status=status.HTTP_201_CREATED)


class CartItemUpdateView(APIView):
    """
    PATCH  /api/cart/items/<id>/   — quantity update
    DELETE /api/cart/items/<id>/   — item remove
    """
    permission_classes = [IsAuthenticated]

    def _get_item(self, pk, user):
        return get_object_or_404(CartItem, pk=pk, cart__user=user)

    def patch(self, request, pk):
        item     = self._get_item(pk, request.user)
        quantity = request.data.get('quantity')

        if not quantity or int(quantity) < 1:
            return Response({"error": "Quantity 1 se kam nahi ho sakti."}, status=400)

        quantity = int(quantity)
        available = item.available_stock
        if available and quantity > available:
            return Response(
                {"error": f"Sirf {available} units available hain."},
                status=400
            )

        item.quantity = quantity
        item.save()
        return Response(CartItemSerializer(item).data)

    def delete(self, request, pk):
        item = self._get_item(pk, request.user)
        item.delete()
        return Response({"message": "Item remove ho gaya."}, status=204)


class ApplyCouponView(APIView):
    """
    POST /api/cart/coupon/apply/
    Body: {"code": "SAVE100"}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ApplyCouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart, _ = Cart.objects.get_or_create(user=request.user)
        coupon = serializer.coupon

        # Min order amount check
        if cart.subtotal < coupon.min_order_amount:
            return Response({
                "error": f"Minimum order Rs {coupon.min_order_amount} chahiye is coupon ke liye."
            }, status=400)

        cart.coupon = coupon
        cart.save()

        discount = coupon.calculate_discount(cart.subtotal)
        return Response({
            "message": f"Coupon '{coupon.code}' apply ho gaya!",
            "discount_amount": discount,
            "total": cart.total,
        })


class RemoveCouponView(APIView):
    """DELETE /api/cart/coupon/remove/"""
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart.coupon = None
        cart.save()
        return Response({"message": "Coupon remove ho gaya."})


class CartSummaryView(APIView):
    """
    GET /api/cart/summary/
    Checkout se pehle final price confirm karne ke liye
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.prefetch_related(
            'items__product', 'items__variant'
        ).get_or_create(user=request.user)

        items_data = []
        for item in cart.items.all():
            items_data.append({
                'name':        item.product.name,
                'variant':     item.variant.name if item.variant else None,
                'quantity':    item.quantity,
                'unit_price':  item.unit_price,
                'total_price': item.total_price,
                'in_stock':    item.available_stock >= item.quantity,
            })

        return Response({
            'items':           items_data,
            'total_items':     cart.total_items,
            'subtotal':        cart.subtotal,
            'coupon':          cart.coupon.code if cart.coupon else None,
            'discount_amount': cart.discount_amount,
            'total':           cart.total,
        })


# ══════════════════════════════════════════════════════════════
# WISHLIST VIEWS
# ══════════════════════════════════════════════════════════════

class WishlistView(APIView):
    """
    GET    /api/wishlist/          — apni wishlist dekho
    POST   /api/wishlist/          — product add karo
    DELETE /api/wishlist/<id>/     — product remove karo
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = WishlistItem.objects.filter(
            user=request.user
        ).select_related('product').prefetch_related('product__images')
        return Response(WishlistItemSerializer(items, many=True).data)

    def post(self, request):
        product_id = request.data.get('product_id')
        if not product_id:
            return Response({"error": "product_id zaroori hai."}, status=400)

        product = get_object_or_404(Product, pk=product_id, status='active')

        item, created = WishlistItem.objects.get_or_create(
            user=request.user, product=product
        )
        if not created:
            return Response({"message": "Product pehle se wishlist mein hai."})

        return Response(WishlistItemSerializer(item).data, status=201)


class WishlistItemDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        item = get_object_or_404(WishlistItem, pk=pk, user=request.user)
        item.delete()
        return Response({"message": "Wishlist se remove ho gaya."}, status=204)


class WishlistMoveToCartView(APIView):
    """
    POST /api/wishlist/<id>/move-to-cart/
    Wishlist item ko seedha cart mein daalo
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        wish_item = get_object_or_404(WishlistItem, pk=pk, user=request.user)
        cart, _   = Cart.objects.get_or_create(user=request.user)

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=wish_item.product,
            variant=None,
            defaults={'quantity': 1}
        )
        if not created:
            cart_item.quantity += 1
            cart_item.save()

        wish_item.delete()
        return Response({
            "message": f"'{wish_item.product.name}' cart mein move ho gaya.",
            "cart_item": CartItemSerializer(cart_item).data,
        })


# ══════════════════════════════════════════════════════════════
# ADMIN — Coupon Management
# ══════════════════════════════════════════════════════════════

class AdminCouponListCreateView(APIView):
    """
    GET  /api/cart/admin/coupons/   — sabhi coupons
    POST /api/cart/admin/coupons/   — naya coupon banao
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        coupons = Coupon.objects.all().order_by('-created_at')
        return Response(CouponSerializer(coupons, many=True).data)

    def post(self, request):
        serializer = CouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        coupon = serializer.save()
        return Response(CouponSerializer(coupon).data, status=201)


class AdminCouponDetailView(APIView):
    """
    PATCH  /api/cart/admin/coupons/<id>/  — update
    DELETE /api/cart/admin/coupons/<id>/  — delete
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def patch(self, request, pk):
        coupon     = get_object_or_404(Coupon, pk=pk)
        serializer = CouponSerializer(coupon, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        coupon = get_object_or_404(Coupon, pk=pk)
        coupon.is_active = False
        coupon.save()
        return Response({"message": "Coupon deactivate ho gaya."}, status=204)
