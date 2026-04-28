import uuid
from django.db import models
from django.core.validators import MinValueValidator
from jwtapp.models import User, Address
from products.models import Product, ProductVariant


# ─── Order ────────────────────────────────────────────────────────────────
class Order(models.Model):
    """
    Main order model.
    Cart se order banta hai — atomic transaction mein.
    """

    class Status(models.TextChoices):
        PENDING    = 'pending',    'Pending'       # Payment nahi hua
        CONFIRMED  = 'confirmed',  'Confirmed'     # Payment hua
        PROCESSING = 'processing', 'Processing'    # Vendor packing kar raha hai
        SHIPPED    = 'shipped',    'Shipped'       # Dispatch ho gaya
        DELIVERED  = 'delivered',  'Delivered'     # Customer ko mila
        CANCELLED  = 'cancelled',  'Cancelled'     # Cancel ho gaya
        REFUNDED   = 'refunded',   'Refunded'      # Refund ho gaya

    class PaymentStatus(models.TextChoices):
        UNPAID   = 'unpaid',   'Unpaid'
        PAID     = 'paid',     'Paid'
        FAILED   = 'failed',   'Failed'
        REFUNDED = 'refunded', 'Refunded'

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_id        = models.CharField(max_length=20, unique=True)  # ORD-XXXXXXXXXX
    user            = models.ForeignKey(User, on_delete=models.PROTECT, related_name='orders')

    # Snapshot of shipping address (address delete ho jaye toh order safe rahe)
    shipping_name   = models.CharField(max_length=200)
    shipping_phone  = models.CharField(max_length=15)
    shipping_line1  = models.CharField(max_length=255)
    shipping_line2  = models.CharField(max_length=255, blank=True)
    shipping_city   = models.CharField(max_length=100)
    shipping_state  = models.CharField(max_length=100)
    shipping_pincode = models.CharField(max_length=10)
    shipping_country = models.CharField(max_length=100, default='India')

    # Pricing snapshot
    subtotal        = models.DecimalField(max_digits=12, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_charge = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total           = models.DecimalField(max_digits=12, decimal_places=2)
    coupon_code     = models.CharField(max_length=50, blank=True)

    status          = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    payment_status  = models.CharField(
        max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID
    )

    notes           = models.TextField(blank=True)  # Customer ke special instructions
    cancel_reason   = models.TextField(blank=True)

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order_id} — {self.user.email}"

    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id = _generate_order_id()
        super().save(*args, **kwargs)

    @property
    def can_cancel(self):
        return self.status in [
            self.Status.PENDING, self.Status.CONFIRMED, self.Status.PROCESSING
        ]

    @property
    def can_refund(self):
        return self.status == self.Status.DELIVERED and \
               self.payment_status == self.PaymentStatus.PAID


# ─── Order Item ───────────────────────────────────────────────────────────
class OrderItem(models.Model):
    """
    Order ka ek product.
    Price snapshot liya jata hai order time pe — future price change affect nahi karega.
    """
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order       = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product     = models.ForeignKey(Product, on_delete=models.PROTECT)
    variant     = models.ForeignKey(
        ProductVariant, on_delete=models.SET_NULL, null=True, blank=True
    )

    # Price snapshot — order ke waqt ka price
    product_name  = models.CharField(max_length=300)
    variant_name  = models.CharField(max_length=100, blank=True)
    unit_price    = models.DecimalField(max_digits=10, decimal_places=2)
    quantity      = models.PositiveIntegerField()
    total_price   = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'order_items'

    def __str__(self):
        return f"{self.product_name} x{self.quantity}"


# ─── Order Tracking ───────────────────────────────────────────────────────
class OrderTracking(models.Model):
    """
    Order ki har status change yahan record hogi.
    Timeline view ke liye.
    """
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order       = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='tracking')
    status      = models.CharField(max_length=20, choices=Order.Status.choices)
    message     = models.CharField(max_length=500)
    location    = models.CharField(max_length=200, blank=True)  # e.g. "Mumbai Hub"
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_by  = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        db_table = 'order_tracking'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order.order_id} — {self.status}"


# ─── Return/Refund Request ────────────────────────────────────────────────
class ReturnRequest(models.Model):
    """Customer delivered order return karna chahta hai."""

    class Status(models.TextChoices):
        PENDING  = 'pending',  'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        REFUNDED = 'refunded', 'Refunded'

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order       = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='return_request')
    user        = models.ForeignKey(User, on_delete=models.CASCADE)
    reason      = models.TextField()
    status      = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    admin_note  = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'return_requests'

    def __str__(self):
        return f"Return: {self.order.order_id} — {self.status}"


# ─── Helper ───────────────────────────────────────────────────────────────
def _generate_order_id():
    import secrets, string
    chars = string.ascii_uppercase + string.digits
    suffix = ''.join(secrets.choice(chars) for _ in range(10))
    return f"ORD-{suffix}"
