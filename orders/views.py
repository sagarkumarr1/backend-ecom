from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import Order, OrderItem, OrderTracking, ReturnRequest
from .serializers import (
    OrderSerializer, PlaceOrderSerializer, CancelOrderSerializer,
    ReturnRequestSerializer, AdminOrderSerializer, OrderTrackingSerializer
)
from cart.models import Cart, CartItem
from jwtapp.permissions import IsAdminUser
from .tasks import send_order_email


# ══════════════════════════════════════════════════════════════
# CUSTOMER ORDER VIEWS
# ══════════════════════════════════════════════════════════════

class PlaceOrderView(APIView):
    """
    POST /api/orders/place/
    Body: {"address_id": "uuid", "notes": "optional"}
    Cart se order atomic transaction mein banta hai.
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = PlaceOrderSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        address = serializer.address
        cart    = Cart.objects.prefetch_related(
            'items__product__stock', 'items__variant'
        ).filter(user=request.user).first()

        if not cart or not cart.items.exists():
            return Response({"error": "Cart khaali hai."}, status=400)

        # ── Stock validation ──────────────────────────────────────────────
        for item in cart.items.all():
            if item.variant:
                if item.variant.stock < item.quantity:
                    return Response({
                        "error": f"'{item.product.name} ({item.variant.name})' ka stock kam hai. "
                                 f"Available: {item.variant.stock}"
                    }, status=400)
            else:
                try:
                    if item.product.stock.quantity < item.quantity:
                        return Response({
                            "error": f"'{item.product.name}' ka stock kam hai. "
                                     f"Available: {item.product.stock.quantity}"
                        }, status=400)
                except Exception:
                    pass

        # ── Create Order ──────────────────────────────────────────────────
        order = Order.objects.create(
            user            = request.user,
            shipping_name   = address.full_name,
            shipping_phone  = address.phone,
            shipping_line1  = address.address_line1,
            shipping_line2  = address.address_line2,
            shipping_city   = address.city,
            shipping_state  = address.state,
            shipping_pincode = address.pincode,
            shipping_country = address.country,
            subtotal        = cart.subtotal,
            discount_amount = cart.discount_amount,
            shipping_charge = 0,
            total           = cart.total,
            coupon_code     = cart.coupon.code if cart.coupon else '',
            notes           = serializer.validated_data.get('notes', ''),
        )

        # ── Create OrderItems + Deduct Stock ──────────────────────────────
        for item in cart.items.all():
            OrderItem.objects.create(
                order        = order,
                product      = item.product,
                variant      = item.variant,
                product_name = item.product.name,
                variant_name = item.variant.name if item.variant else '',
                unit_price   = item.unit_price,
                quantity     = item.quantity,
                total_price  = item.total_price,
            )
            # Stock deduct
            if item.variant:
                item.variant.stock -= item.quantity
                item.variant.save(update_fields=['stock'])
            else:
                try:
                    item.product.stock.quantity -= item.quantity
                    item.product.stock.save(update_fields=['quantity'])
                except Exception:
                    pass

            # total_sold update
            item.product.total_sold += item.quantity
            item.product.save(update_fields=['total_sold'])

        # ── First Tracking Entry ──────────────────────────────────────────
        OrderTracking.objects.create(
            order   = order,
            status  = Order.Status.PENDING,
            message = "Order place ho gaya! Payment ka intezaar hai.",
        )

        # ── Clear Cart ────────────────────────────────────────────────────
        cart.items.all().delete()
        cart.coupon = None
        cart.save()

        # ── Send Email (async) ────────────────────────────────────────────
        try:
            send_order_email(request.user.email, order.order_id, 'placed')
        except Exception:
            pass

        return Response({
            "message":  "Order place ho gaya!",
            "order_id": order.order_id,
            "total":    order.total,
            "order":    OrderSerializer(order).data,
        }, status=201)


class OrderListView(APIView):
    """GET /api/orders/ — apne saare orders"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(
            user=request.user
        ).prefetch_related('items', 'tracking').order_by('-created_at')

        # Filter by status
        status_param = request.query_params.get('status')
        if status_param:
            orders = orders.filter(status=status_param)

        return Response(OrderSerializer(orders, many=True).data)


class OrderDetailView(APIView):
    """GET /api/orders/<order_id>/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        order = get_object_or_404(
            Order.objects.prefetch_related('items', 'tracking'),
            order_id=order_id, user=request.user
        )
        return Response(OrderSerializer(order).data)


class CancelOrderView(APIView):
    """
    POST /api/orders/<order_id>/cancel/
    Body: {"reason": "optional reason"}
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, order_id):
        order = get_object_or_404(Order, order_id=order_id, user=request.user)

        if not order.can_cancel:
            return Response({
                "error": f"'{order.status}' status mein order cancel nahi ho sakta."
            }, status=400)

        serializer = CancelOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get('reason', 'Customer ne cancel kiya')

        # Stock restore karo
        for item in order.items.all():
            if item.variant:
                item.variant.stock += item.quantity
                item.variant.save(update_fields=['stock'])
            else:
                try:
                    item.product.stock.quantity += item.quantity
                    item.product.stock.save(update_fields=['quantity'])
                except Exception:
                    pass
            item.product.total_sold = max(0, item.product.total_sold - item.quantity)
            item.product.save(update_fields=['total_sold'])

        order.status        = Order.Status.CANCELLED
        order.cancel_reason = reason
        order.save()

        OrderTracking.objects.create(
            order      = order,
            status     = Order.Status.CANCELLED,
            message    = f"Order cancel ho gaya. Reason: {reason}",
            updated_by = request.user,
        )

        try:
            send_order_email(request.user.email, order.order_id, 'cancelled')
        except Exception:
            pass

        return Response({"message": "Order cancel ho gaya.", "order_id": order.order_id})


class OrderTrackingView(APIView):
    """GET /api/orders/<order_id>/tracking/ — tracking timeline"""
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        order    = get_object_or_404(Order, order_id=order_id, user=request.user)
        tracking = order.tracking.all().order_by('created_at')
        return Response({
            "order_id":      order.order_id,
            "current_status": order.status,
            "timeline":      OrderTrackingSerializer(tracking, many=True).data,
        })


class ReturnRequestView(APIView):
    """
    POST /api/orders/<order_id>/return/
    Body: {"reason": "Product damage tha"}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        order = get_object_or_404(Order, order_id=order_id, user=request.user)

        if not order.can_refund:
            return Response({"error": "Return sirf delivered orders ke liye possible hai."}, status=400)

        if hasattr(order, 'return_request'):
            return Response({"error": "Return request pehle se exist karti hai."}, status=400)

        serializer = ReturnRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return_req = ReturnRequest.objects.create(
            order  = order,
            user   = request.user,
            reason = serializer.validated_data['reason'],
        )
        return Response(ReturnRequestSerializer(return_req).data, status=201)


# ══════════════════════════════════════════════════════════════
# ADMIN ORDER VIEWS
# ══════════════════════════════════════════════════════════════

class AdminOrderListView(APIView):
    """
    GET /api/orders/admin/           — sabhi orders
    GET /api/orders/admin/?status=pending
    GET /api/orders/admin/?search=ORD-xxx
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        orders = Order.objects.select_related('user').prefetch_related('items')

        status_param = request.query_params.get('status')
        search       = request.query_params.get('search')
        payment      = request.query_params.get('payment_status')

        if status_param:
            orders = orders.filter(status=status_param)
        if payment:
            orders = orders.filter(payment_status=payment)
        if search:
            orders = orders.filter(order_id__icontains=search)

        return Response({
            "count":  orders.count(),
            "orders": AdminOrderSerializer(orders, many=True).data,
        })


class AdminOrderDetailView(APIView):
    """GET /api/orders/admin/<order_id>/"""
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, order_id):
        order = get_object_or_404(
            Order.objects.prefetch_related('items', 'tracking'),
            order_id=order_id
        )
        return Response(AdminOrderSerializer(order).data)


class AdminUpdateOrderStatusView(APIView):
    """
    PATCH /api/orders/admin/<order_id>/status/
    Body: {"status": "shipped", "message": "Dispatched from Mumbai", "location": "Mumbai Hub"}
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def patch(self, request, order_id):
        order      = get_object_or_404(Order, order_id=order_id)
        new_status = request.data.get('status')
        message    = request.data.get('message', '')
        location   = request.data.get('location', '')

        valid_statuses = [s[0] for s in Order.Status.choices]
        if new_status not in valid_statuses:
            return Response({"error": f"Invalid status: {new_status}"}, status=400)

        order.status = new_status
        if new_status == Order.Status.CONFIRMED:
            order.payment_status = Order.PaymentStatus.PAID
        order.save()

        # Tracking entry
        default_messages = {
            'confirmed':  'Order confirm ho gaya! Payment receive hua.',
            'processing': 'Order pack ho raha hai.',
            'shipped':    'Order dispatch ho gaya.',
            'delivered':  'Order deliver ho gaya!',
            'cancelled':  'Order cancel ho gaya.',
            'refunded':   'Refund process ho gaya.',
        }
        OrderTracking.objects.create(
            order      = order,
            status     = new_status,
            message    = message or default_messages.get(new_status, ''),
            location   = location,
            updated_by = request.user,
        )

        try:
            send_order_email(order.user.email, order.order_id, new_status)
        except Exception:
            pass

        return Response({
            "message":    f"Order status '{new_status}' update ho gaya.",
            "order_id":   order.order_id,
            "new_status": order.status,
        })


class AdminReturnListView(APIView):
    """GET /api/orders/admin/returns/ — sabhi return requests"""
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        returns = ReturnRequest.objects.select_related('order', 'user')
        status_param = request.query_params.get('status')
        if status_param:
            returns = returns.filter(status=status_param)
        return Response(ReturnRequestSerializer(returns, many=True).data)


class AdminReturnActionView(APIView):
    """
    PATCH /api/orders/admin/returns/<id>/
    Body: {"status": "approved", "admin_note": "Refund process hoga"}
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    @transaction.atomic
    def patch(self, request, pk):
        return_req = get_object_or_404(ReturnRequest, pk=pk)
        new_status = request.data.get('status')
        admin_note = request.data.get('admin_note', '')

        valid = ['approved', 'rejected', 'refunded']
        if new_status not in valid:
            return Response({"error": "Invalid status."}, status=400)

        return_req.status     = new_status
        return_req.admin_note = admin_note
        return_req.save()

        # Agar refunded — order status bhi update karo
        if new_status == 'refunded':
            return_req.order.status         = Order.Status.REFUNDED
            return_req.order.payment_status = Order.PaymentStatus.REFUNDED
            return_req.order.save()

        return Response(ReturnRequestSerializer(return_req).data)
