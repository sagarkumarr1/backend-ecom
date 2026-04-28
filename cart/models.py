import uuid
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from jwtapp.models import User
from products.models import Product, ProductVariant


# ─── Coupon ───────────────────────────────────────────────────────────────
class Coupon(models.Model):
    """
    Discount coupon — flat ya percentage.
    Example: SAVE100 = Rs 100 off, SUMMER10 = 10% off
    """

    class DiscountType(models.TextChoices):
        FLAT       = 'flat',       'Flat Amount'
        PERCENTAGE = 'percentage', 'Percentage'

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code            = models.CharField(max_length=50, unique=True)
    description     = models.CharField(max_length=200, blank=True)
    discount_type   = models.CharField(max_length=15, choices=DiscountType.choices, default=DiscountType.FLAT)
    discount_value  = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_discount     = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )  # Percentage discount pe max cap
    usage_limit     = models.PositiveIntegerField(default=1)   # Total kitni baar use ho sakta
    used_count      = models.PositiveIntegerField(default=0)
    is_active       = models.BooleanField(default=True)
    valid_from      = models.DateTimeField(default=timezone.now)
    valid_until     = models.DateTimeField(null=True, blank=True)

    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'coupons'

    def __str__(self):
        return f"{self.code} ({self.discount_type}: {self.discount_value})"

    @property
    def is_valid(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.used_count >= self.usage_limit:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True

    def calculate_discount(self, order_amount):
        """Order amount pe discount calculate karo."""
        if order_amount < self.min_order_amount:
            return 0

        if self.discount_type == self.DiscountType.FLAT:
            return min(self.discount_value, order_amount)
        else:
            discount = (order_amount * self.discount_value) / 100
            if self.max_discount:
                discount = min(discount, self.max_discount)
            return round(discount, 2)


# ─── Cart ─────────────────────────────────────────────────────────────────
class Cart(models.Model):
    """
    Ek user ka ek cart hoga.
    get_or_create se automatically banta hai.
    """
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    coupon     = models.ForeignKey(
        Coupon, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'carts'

    def __str__(self):
        return f"Cart of {self.user.email}"

    @property
    def subtotal(self):
        """Discount se pehle total."""
        return sum(item.total_price for item in self.items.all())

    @property
    def discount_amount(self):
        if self.coupon and self.coupon.is_valid:
            return self.coupon.calculate_discount(self.subtotal)
        return 0

    @property
    def total(self):
        """Final total — coupon discount ke baad."""
        return max(self.subtotal - self.discount_amount, 0)

    @property
    def total_items(self):
        return self.items.count()


# ─── Cart Item ────────────────────────────────────────────────────────────
class CartItem(models.Model):
    """
    Cart ka ek item — product ya variant ke saath quantity.
    """
    id       = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart     = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product  = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant  = models.ForeignKey(
        ProductVariant, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cart_items'
        unique_together = ('cart', 'product', 'variant')  # Duplicate item nahi

    def __str__(self):
        variant_info = f" ({self.variant.name})" if self.variant else ""
        return f"{self.product.name}{variant_info} x{self.quantity}"

    @property
    def unit_price(self):
        """Variant ka price ya product ka discounted price."""
        if self.variant:
            return self.variant.final_price
        return self.product.discounted_price

    @property
    def total_price(self):
        return self.unit_price * self.quantity

    @property
    def available_stock(self):
        """Kitna stock available hai."""
        if self.variant:
            return self.variant.stock
        try:
            return self.product.stock.quantity
        except Exception:
            return 0


# ─── Wishlist ─────────────────────────────────────────────────────────────
class WishlistItem(models.Model):
    """
    User ke saved products.
    Simple — sirf product, koi variant/quantity nahi.
    """
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist')
    product    = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table        = 'wishlist_items'
        unique_together = ('user', 'product')  # Ek product ek baar

    def __str__(self):
        return f"{self.user.email} — {self.product.name}"
