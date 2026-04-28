import uuid
from django.db import models
from django.core.validators import MinValueValidator
from django.utils.text import slugify
from jwtapp.models import User


# ─── Category ─────────────────────────────────────────────────────────────
class Category(models.Model):
    """
    Self-referential — parent/child categories.
    Example: Electronics > Phones > Smartphones
    """
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name        = models.CharField(max_length=200)
    slug        = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(blank=True)
    image       = models.URLField(blank=True)
    parent      = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='children'
    )
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table            = 'categories'
        verbose_name_plural = 'Categories'
        ordering            = ['name']

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # Duplicate slug hone pe unique banao
            original_slug = self.slug
            counter = 1
            while Category.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)


# ─── Product ──────────────────────────────────────────────────────────────
class Product(models.Model):
    """
    Main product model.
    Vendor apna product list karta hai.
    Admin approve karta hai.
    """

    class Status(models.TextChoices):
        DRAFT     = 'draft',     'Draft'
        ACTIVE    = 'active',    'Active'
        INACTIVE  = 'inactive',  'Inactive'
        REJECTED  = 'rejected',  'Rejected'

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor      = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='products',
        limit_choices_to={'role': 'vendor'}
    )
    category    = models.ForeignKey(
        Category, on_delete=models.SET_NULL,
        null=True, related_name='products'
    )

    name        = models.CharField(max_length=300)
    slug        = models.SlugField(max_length=320, unique=True, blank=True)
    description = models.TextField()
    price       = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    discount_percent = models.PositiveIntegerField(default=0)  # 0-100
    brand       = models.CharField(max_length=200, blank=True)
    sku         = models.CharField(max_length=100, unique=True, blank=True)

    status      = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    is_featured = models.BooleanField(default=False)

    # Rating — review save hone ke baad update hoga (signal se)
    avg_rating    = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_reviews = models.PositiveIntegerField(default=0)
    total_sold    = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def discounted_price(self):
        """Discount ke baad actual price."""
        if self.discount_percent > 0:
            discount = (self.price * self.discount_percent) / 100
            return round(self.price - discount, 2)
        return self.price

    @property
    def is_in_stock(self):
        """Koi bhi variant/stock available hai?"""
        if self.variants.exists():
            return self.variants.filter(stock__gt=0).exists()
        return self.stock_quantity > 0

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            original_slug = self.slug
            counter = 1
            while Product.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        if not self.sku:
            import random, string
            self.sku = 'SKU-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        super().save(*args, **kwargs)


# ─── Product Image ────────────────────────────────────────────────────────
class ProductImage(models.Model):
    """
    Ek product ke multiple images.
    primary=True wali image thumbnail hogi.
    """
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product    = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image_url  = models.URLField()         # Cloudinary URL
    alt_text   = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    order      = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'product_images'
        ordering = ['order', '-is_primary']

    def __str__(self):
        return f"{self.product.name} — Image {self.order}"

    def save(self, *args, **kwargs):
        # Ek product ka sirf ek primary image
        if self.is_primary:
            ProductImage.objects.filter(
                product=self.product, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


# ─── Product Variant ──────────────────────────────────────────────────────
class ProductVariant(models.Model):
    """
    Size, Color, etc. ke variants.
    Example: T-shirt → [Small/Red, Medium/Blue, Large/Green]
    """
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product       = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name          = models.CharField(max_length=100)   # e.g. "Small / Red"
    size          = models.CharField(max_length=50, blank=True)
    color         = models.CharField(max_length=50, blank=True)
    extra_price   = models.DecimalField(
        max_digits=8, decimal_places=2, default=0.00,
        validators=[MinValueValidator(0)]
    )   # Base price ke upar extra
    stock         = models.PositiveIntegerField(default=0)
    sku           = models.CharField(max_length=100, unique=True, blank=True)
    image_url     = models.URLField(blank=True)
    is_active     = models.BooleanField(default=True)

    class Meta:
        db_table = 'product_variants'
        ordering = ['name']

    def __str__(self):
        return f"{self.product.name} — {self.name}"

    @property
    def final_price(self):
        return self.product.discounted_price + self.extra_price

    @property
    def is_in_stock(self):
        return self.stock > 0

    def save(self, *args, **kwargs):
        if not self.sku:
            import random, string
            self.sku = 'VAR-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        super().save(*args, **kwargs)


# ─── Stock (simple, no variants) ──────────────────────────────────────────
class Stock(models.Model):
    """
    Simple stock — variant nahi hain toh yahan track hoga.
    """
    product        = models.OneToOneField(
        Product, on_delete=models.CASCADE, related_name='stock'
    )
    quantity       = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'product_stock'

    def __str__(self):
        return f"{self.product.name} — Stock: {self.quantity}"

    @property
    def is_low_stock(self):
        return self.quantity <= self.low_stock_threshold

    @property
    def is_out_of_stock(self):
        return self.quantity == 0
