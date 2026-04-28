import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from datetime import timedelta


# ─── User Manager ─────────────────────────────────────────────────────────
class UserManager(BaseUserManager):

    def create_user(self, email, full_name, password=None, **extra_fields):
        if not email:
            raise ValueError("Email zaroori hai")
        email = self.normalize_email(email)
        extra_fields.setdefault('role', 'customer')
        extra_fields.setdefault('is_active', True)
        user = self.model(email=email, full_name=full_name, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, full_name, password=None, **extra_fields):
        extra_fields['role']              = 'admin'
        extra_fields['is_staff']          = True
        extra_fields['is_superuser']      = True
        extra_fields['is_email_verified'] = True
        return self.create_user(email, full_name, password, **extra_fields)


# ─── User Model ───────────────────────────────────────────────────────────
class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model — email se login, 3 roles: customer / vendor / admin
    UUID primary key — integer ID se zyada secure
    """

    CUSTOMER = 'customer'
    VENDOR   = 'vendor'
    ADMIN    = 'admin'

    ROLE_CHOICES = [
        (CUSTOMER, 'Customer'),
        (VENDOR,   'Vendor'),
        (ADMIN,    'Admin'),
    ]

    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email     = models.EmailField(unique=True)
    mobile    = models.CharField(max_length=15, unique=True, null=True, blank=True)
    full_name = models.CharField(max_length=255)
    role      = models.CharField(max_length=20, choices=ROLE_CHOICES, default=CUSTOMER)

    is_active         = models.BooleanField(default=True)
    is_staff          = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)

    # Google OAuth2
    google_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    avatar    = models.URLField(null=True, blank=True)

    # Vendor specific
    shop_name          = models.CharField(max_length=200, null=True, blank=True)
    shop_description   = models.TextField(null=True, blank=True)
    is_vendor_approved = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['full_name']

    objects = UserManager()

    class Meta:
        db_table     = 'users'
        verbose_name = 'User'
        ordering     = ['-created_at']

    def __str__(self):
        return f"{self.email} [{self.role}]"

    @property
    def is_customer(self):
        return self.role == self.CUSTOMER

    @property
    def is_vendor(self):
        return self.role == self.VENDOR

    @property
    def is_admin_user(self):
        return self.role == self.ADMIN


# ─── Address Model (NEW - Day 1) ──────────────────────────────────────────
class Address(models.Model):
    """
    Shipping address book — ek user ke multiple addresses.
    Order place karte waqt koi ek select hoga.
    """

    class AddressType(models.TextChoices):
        HOME  = 'home',  'Home'
        WORK  = 'work',  'Work'
        OTHER = 'other', 'Other'

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    full_name     = models.CharField(max_length=200)
    phone         = models.CharField(max_length=15)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city          = models.CharField(max_length=100)
    state         = models.CharField(max_length=100)
    pincode       = models.CharField(max_length=10)
    country       = models.CharField(max_length=100, default='India')
    address_type  = models.CharField(
        max_length=10,
        choices=AddressType.choices,
        default=AddressType.HOME
    )
    is_default    = models.BooleanField(default=False)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table            = 'user_addresses'
        verbose_name_plural = 'Addresses'
        ordering            = ['-is_default', '-created_at']

    def __str__(self):
        return f"{self.full_name} — {self.city}, {self.state}"

    def save(self, *args, **kwargs):
        # Is address ko default banane se pehle baaki sab ka default hata do
        if self.is_default:
            Address.objects.filter(
                user=self.user, is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


# ─── OTP Verification ─────────────────────────────────────────────────────
class OTPVerification(models.Model):
    """
    Email verify aur password reset dono ke liye ek hi table.
    OTP 10 minute mein expire hota hai.
    """

    PURPOSE_EMAIL_VERIFY   = 'email_verify'
    PURPOSE_PASSWORD_RESET = 'password_reset'

    PURPOSE_CHOICES = [
        (PURPOSE_EMAIL_VERIFY,   'Email Verify'),
        (PURPOSE_PASSWORD_RESET, 'Password Reset'),
    ]

    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otps')
    otp        = models.CharField(max_length=6)
    purpose    = models.CharField(max_length=30, choices=PURPOSE_CHOICES)
    is_used    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = 'otp_verifications'

    def __str__(self):
        return f"{self.user.email} — {self.purpose}"

    def is_expired(self):
        return timezone.now() > self.expires_at

    @classmethod
    def create_otp(cls, user, purpose):
        import random
        # Purane unused OTPs delete karo
        cls.objects.filter(user=user, purpose=purpose, is_used=False).delete()
        otp_code = f"{random.randint(100000, 999999)}"
        return cls.objects.create(
            user=user,
            otp=otp_code,
            purpose=purpose,
            expires_at=timezone.now() + timedelta(minutes=10),
        )
