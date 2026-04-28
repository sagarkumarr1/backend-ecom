import hmac
import hashlib
import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import Payment, Refund
from .serializers import PaymentSerializer, RefundSerializer
from orders.models import Order
from jwtapp.permissions import IsAdminUser


def get_razorpay_client():
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


# ══════════════════════════════════════════════════════════════
# PAYMENT VIEWS
# ══════════════════════════════════════════════════════════════

class CreatePaymentView(APIView):
    """
    POST /api/payments/create/
    Body: {"order_id": "ORD-XXXXXXXXXX"}

    Razorpay order create karta hai.
    Frontend is order ID se payment modal open karega.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order_id = request.data.get('order_id')
        if not order_id:
            return Response({"error": "order_id zaroori hai."}, status=400)

        order = get_object_or_404(Order, order_id=order_id, user=request.user)

        if order.payment_status == Order.PaymentStatus.PAID:
            return Response({"error": "Order ka payment pehle se ho chuka hai."}, status=400)

        # Agar payment pehle se create hua hai — wahi return karo
        if hasattr(order, 'payment') and order.payment.status == Payment.Status.CREATED:
            return Response({
                "razorpay_order_id": order.payment.razorpay_order_id,
                "amount":            int(order.total * 100),  # paise mein
                "currency":          "INR",
                "key":               settings.RAZORPAY_KEY_ID,
                "order_id":          order.order_id,
            })

        # Razorpay order banao
        try:
            client = get_razorpay_client()
            rz_order = client.order.create({
                "amount":   int(order.total * 100),  # paise mein
                "currency": "INR",
                "receipt":  order.order_id,
                "notes": {
                    "order_id":   order.order_id,
                    "user_email": request.user.email,
                }
            })
        except Exception as e:
            return Response({"error": f"Razorpay error: {str(e)}"}, status=500)

        # Payment record banao
        Payment.objects.filter(order=order).delete()  # old pending cleanup
        payment = Payment.objects.create(
            order             = order,
            user              = request.user,
            razorpay_order_id = rz_order['id'],
            amount            = order.total,
            status            = Payment.Status.CREATED,
        )

        return Response({
            "razorpay_order_id": rz_order['id'],
            "amount":            int(order.total * 100),
            "currency":          "INR",
            "key":               settings.RAZORPAY_KEY_ID,
            "order_id":          order.order_id,
            "name":              "My Ecommerce Store",
            "description":       f"Order {order.order_id}",
            "prefill": {
                "name":    request.user.full_name,
                "email":   request.user.email,
                "contact": request.user.mobile or '',
            }
        })


class VerifyPaymentView(APIView):
    """
    POST /api/payments/verify/
    Body: {
        "razorpay_order_id":   "order_xxx",
        "razorpay_payment_id": "pay_xxx",
        "razorpay_signature":  "signature_xxx"
    }
    Frontend payment ke baad yeh call karo — signature verify hoga.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        rz_order_id   = request.data.get('razorpay_order_id')
        rz_payment_id = request.data.get('razorpay_payment_id')
        rz_signature  = request.data.get('razorpay_signature')

        if not all([rz_order_id, rz_payment_id, rz_signature]):
            return Response({"error": "Teeno fields zaroori hain."}, status=400)

        payment = get_object_or_404(Payment, razorpay_order_id=rz_order_id, user=request.user)

        # ── HMAC Signature Verify ─────────────────────────────────────────
        body        = f"{rz_order_id}|{rz_payment_id}"
        expected_sig = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode(),
            body.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_sig, rz_signature):
            payment.status = Payment.Status.FAILED
            payment.save()
            return Response({"error": "Payment signature invalid hai. Possible fraud!"}, status=400)

        # ── Payment Successful ────────────────────────────────────────────
        payment.razorpay_payment_id = rz_payment_id
        payment.razorpay_signature  = rz_signature
        payment.status              = Payment.Status.SUCCESS
        payment.save()

        # Order update
        order = payment.order
        order.status         = Order.Status.CONFIRMED
        order.payment_status = Order.PaymentStatus.PAID
        order.save()

        # Tracking entry
        from orders.models import OrderTracking
        OrderTracking.objects.create(
            order   = order,
            status  = Order.Status.CONFIRMED,
            message = "Payment successful! Order confirm ho gaya.",
        )

        return Response({
            "message":  "Payment successful!",
            "order_id": order.order_id,
            "status":   "confirmed",
        })


@method_decorator(csrf_exempt, name='dispatch')
class RazorpayWebhookView(APIView):
    """
    POST /api/payments/webhook/
    Razorpay dashboard mein set karo:
    URL: https://yourapi.railway.app/api/payments/webhook/
    Secret: RAZORPAY_WEBHOOK_SECRET (.env mein)

    Yeh automatic call hoga Razorpay se — backup payment confirmation.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        webhook_secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', '')
        webhook_sig    = request.headers.get('X-Razorpay-Signature', '')

        # ── Signature Verify ─────────────────────────────────────────────
        if webhook_secret:
            body = request.body
            expected = hmac.new(
                webhook_secret.encode(),
                body,
                hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(expected, webhook_sig):
                return Response({"error": "Invalid webhook signature."}, status=400)

        event   = request.data.get('event')
        payload = request.data.get('payload', {})

        if event == 'payment.captured':
            rz_payment_id = payload.get('payment', {}).get('entity', {}).get('id')
            rz_order_id   = payload.get('payment', {}).get('entity', {}).get('order_id')

            try:
                payment = Payment.objects.get(razorpay_order_id=rz_order_id)
                if payment.status != Payment.Status.SUCCESS:
                    payment.razorpay_payment_id = rz_payment_id
                    payment.status              = Payment.Status.SUCCESS
                    payment.save()

                    order = payment.order
                    order.status         = Order.Status.CONFIRMED
                    order.payment_status = Order.PaymentStatus.PAID
                    order.save()
            except Payment.DoesNotExist:
                pass

        elif event == 'payment.failed':
            rz_order_id = payload.get('payment', {}).get('entity', {}).get('order_id')
            try:
                payment = Payment.objects.get(razorpay_order_id=rz_order_id)
                payment.status = Payment.Status.FAILED
                payment.save()
            except Payment.DoesNotExist:
                pass

        return Response({"status": "ok"})


class InitiateRefundView(APIView):
    """
    POST /api/payments/refund/
    Body: {"order_id": "ORD-xxx", "reason": "optional"}
    Admin ya customer (approved return ke baad) refund kar sakta hai.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        order_id = request.data.get('order_id')
        reason   = request.data.get('reason', 'Customer request')

        order   = get_object_or_404(Order, order_id=order_id)
        payment = get_object_or_404(Payment, order=order, status=Payment.Status.SUCCESS)

        try:
            client    = get_razorpay_client()
            rz_refund = client.payment.refund(payment.razorpay_payment_id, {
                "amount": int(payment.amount * 100),
                "notes":  {"reason": reason}
            })

            refund = Refund.objects.create(
                payment            = payment,
                razorpay_refund_id = rz_refund['id'],
                amount             = payment.amount,
                reason             = reason,
                status             = Refund.Status.PROCESSED,
            )

            payment.status              = Payment.Status.REFUNDED
            payment.save()
            order.payment_status        = Order.PaymentStatus.REFUNDED
            order.status                = Order.Status.REFUNDED
            order.save()

            return Response({
                "message":   "Refund initiate ho gaya!",
                "refund_id": rz_refund['id'],
                "amount":    payment.amount,
            })

        except Exception as e:
            return Response({"error": f"Refund failed: {str(e)}"}, status=500)


class PaymentDetailView(APIView):
    """GET /api/payments/<order_id>/ — payment status check"""
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        order   = get_object_or_404(Order, order_id=order_id, user=request.user)
        payment = get_object_or_404(Payment, order=order)
        return Response(PaymentSerializer(payment).data)
