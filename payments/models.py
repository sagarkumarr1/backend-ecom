import uuid
from django.db import models
from orders.models import Order
from jwtapp.models import User


class Payment(models.Model):
    """
    Razorpay payment record.
    Order ke saath linked.
    """

    class Status(models.TextChoices):
        CREATED  = 'created',  'Created'
        PENDING  = 'pending',  'Pending'
        SUCCESS  = 'success',  'Success'
        FAILED   = 'failed',   'Failed'
        REFUNDED = 'refunded', 'Refunded'

    id                  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order               = models.OneToOneField(Order, on_delete=models.PROTECT, related_name='payment')
    user                = models.ForeignKey(User, on_delete=models.PROTECT)

    # Razorpay IDs
    razorpay_order_id   = models.CharField(max_length=100, unique=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    razorpay_signature  = models.CharField(max_length=300, blank=True)

    amount              = models.DecimalField(max_digits=12, decimal_places=2)
    currency            = models.CharField(max_length=5, default='INR')
    status              = models.CharField(max_length=20, choices=Status.choices, default=Status.CREATED)

    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order.order_id} — {self.status} — Rs {self.amount}"


class Refund(models.Model):
    """Refund record — Razorpay pe refund initiate karne ke baad."""

    class Status(models.TextChoices):
        PENDING   = 'pending',   'Pending'
        PROCESSED = 'processed', 'Processed'
        FAILED    = 'failed',    'Failed'

    id                 = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment            = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name='refunds')
    razorpay_refund_id = models.CharField(max_length=100, blank=True)
    amount             = models.DecimalField(max_digits=12, decimal_places=2)
    reason             = models.TextField(blank=True)
    status             = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at         = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'refunds'

    def __str__(self):
        return f"Refund {self.razorpay_refund_id} — Rs {self.amount}"
