"""
tests/factories.py
Factory Boy — test data banane ke liye.
Har test mein manually object banane ki zaroorat nahi.
"""
import factory
from factory.django import DjangoModelFactory
from django.utils import timezone
from datetime import timedelta

from jwtapp.models import User, Address
from products.models import Category, Product, ProductImage, ProductVariant, Stock
from cart.models import Cart, CartItem, Coupon, WishlistItem
from orders.models import Order, OrderItem, OrderTracking
from payments.models import Payment
from reviews.models import Review


# ─── User Factories ───────────────────────────────────────────────────────

class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email             = factory.Sequence(lambda n: f'user{n}@test.com')
    full_name         = factory.Faker('name')
    password          = factory.PostGenerationMethodCall('set_password', 'Secure@1234')
    role              = 'customer'
    is_email_verified = True
    is_active         = True


class VendorFactory(DjangoModelFactory):
    class Meta:
        model = User

    email              = factory.Sequence(lambda n: f'vendor{n}@test.com')
    full_name          = factory.Faker('name')
    password           = factory.PostGenerationMethodCall('set_password', 'Secure@1234')
    role               = 'vendor'
    shop_name          = factory.Sequence(lambda n: f'Test Shop {n}')
    shop_description   = 'Quality products'
    is_email_verified  = True
    is_vendor_approved = True
    is_active          = True


class AdminFactory(DjangoModelFactory):
    class Meta:
        model = User

    email             = factory.Sequence(lambda n: f'admin{n}@test.com')
    full_name         = 'Admin User'
    password          = factory.PostGenerationMethodCall('set_password', 'Admin@1234')
    role              = 'admin'
    is_staff          = True
    is_superuser      = True
    is_email_verified = True


class AddressFactory(DjangoModelFactory):
    class Meta:
        model = Address

    user          = factory.SubFactory(UserFactory)
    full_name     = factory.Faker('name')
    phone         = '9876543210'
    address_line1 = factory.Faker('street_address')
    city          = 'Mumbai'
    state         = 'Maharashtra'
    pincode       = '400001'
    country       = 'India'
    address_type  = 'home'
    is_default    = True


# ─── Product Factories ────────────────────────────────────────────────────

class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category

    name      = factory.Sequence(lambda n: f'Category {n}')
    is_active = True


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product

    vendor      = factory.SubFactory(VendorFactory)
    category    = factory.SubFactory(CategoryFactory)
    name        = factory.Sequence(lambda n: f'Product {n}')
    description = factory.Faker('paragraph')
    price       = factory.Faker('pydecimal', left_digits=4, right_digits=2, positive=True)
    status      = 'active'
    brand       = 'TestBrand'

    @factory.post_generation
    def with_stock(obj, create, extracted, **kwargs):
        if create:
            Stock.objects.get_or_create(product=obj, defaults={'quantity': 100})


class ProductVariantFactory(DjangoModelFactory):
    class Meta:
        model = ProductVariant

    product     = factory.SubFactory(ProductFactory)
    name        = factory.Sequence(lambda n: f'Variant {n}')
    size        = 'M'
    color       = 'Red'
    extra_price = 0
    stock       = 50
    is_active   = True


# ─── Cart Factories ───────────────────────────────────────────────────────

class CouponFactory(DjangoModelFactory):
    class Meta:
        model = Coupon

    code           = factory.Sequence(lambda n: f'COUPON{n}')
    discount_type  = 'flat'
    discount_value = 100
    usage_limit    = 100
    is_active      = True
    valid_until    = factory.LazyFunction(lambda: timezone.now() + timedelta(days=30))


class CartFactory(DjangoModelFactory):
    class Meta:
        model = Cart

    user = factory.SubFactory(UserFactory)


class CartItemFactory(DjangoModelFactory):
    class Meta:
        model = CartItem

    cart     = factory.SubFactory(CartFactory)
    product  = factory.SubFactory(ProductFactory)
    quantity = 1


# ─── Order Factories ──────────────────────────────────────────────────────

class OrderFactory(DjangoModelFactory):
    class Meta:
        model = Order

    user             = factory.SubFactory(UserFactory)
    shipping_name    = factory.Faker('name')
    shipping_phone   = '9876543210'
    shipping_line1   = '123 Test Street'
    shipping_city    = 'Mumbai'
    shipping_state   = 'Maharashtra'
    shipping_pincode = '400001'
    subtotal         = 1000
    discount_amount  = 0
    shipping_charge  = 0
    total            = 1000
    status           = 'pending'
    payment_status   = 'unpaid'


class OrderItemFactory(DjangoModelFactory):
    class Meta:
        model = OrderItem

    order        = factory.SubFactory(OrderFactory)
    product      = factory.SubFactory(ProductFactory)
    product_name = 'Test Product'
    unit_price   = 500
    quantity     = 2
    total_price  = 1000


class PaymentFactory(DjangoModelFactory):
    class Meta:
        model = Payment

    order               = factory.SubFactory(OrderFactory)
    user                = factory.SelfAttribute('order.user')
    razorpay_order_id   = factory.Sequence(lambda n: f'order_{n}')
    razorpay_payment_id = factory.Sequence(lambda n: f'pay_{n}')
    amount              = 1000
    status              = 'success'


# ─── Review Factories ─────────────────────────────────────────────────────

class ReviewFactory(DjangoModelFactory):
    class Meta:
        model = Review

    product              = factory.SubFactory(ProductFactory)
    user                 = factory.SubFactory(UserFactory)
    rating               = 4
    title                = 'Good product'
    body                 = 'Mujhe pasand aaya'
    is_verified_purchase = False
    is_approved          = True
