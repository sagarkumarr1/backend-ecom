from django.urls import path
from .views import (
    CreatePaymentView, VerifyPaymentView,
    RazorpayWebhookView, InitiateRefundView, PaymentDetailView,
)

urlpatterns = [
    path('create/',          CreatePaymentView.as_view(),   name='payment_create'),
    path('verify/',          VerifyPaymentView.as_view(),   name='payment_verify'),
    path('webhook/',         RazorpayWebhookView.as_view(), name='payment_webhook'),
    path('refund/',          InitiateRefundView.as_view(),  name='payment_refund'),
    path('<str:order_id>/',  PaymentDetailView.as_view(),   name='payment_detail'),
]
