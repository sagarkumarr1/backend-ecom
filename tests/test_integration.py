"""
tests/test_integration.py
Day 13 — Full Integration Tests
Poora flow test karo — register se lekar order deliver tak.
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock

from tests.factories import (
    UserFactory, VendorFactory, AdminFactory, AddressFactory,
    CategoryFactory, ProductFactory, CouponFactory, OrderFactory,
    OrderItemFactory, PaymentFactory, ReviewFactory,
)
from products.models import Stock
from orders.models import Order, OrderTracking
from payments.models import Payment


# ══════════════════════════════════════════════════════════════
# HELPER
# ══════════════════════════════════════════════════════════════

def auth_client(user, password='Secure@1234'):
    client = APIClient()
    res = client.post(reverse('auth_login'), {'email': user.email, 'password': password})
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
    return client


# ══════════════════════════════════════════════════════════════
# DAY 13 — AUTH INTEGRATION TESTS
# ══════════════════════════════════════════════════════════════

class AuthFlowTest(TestCase):

    def test_full_register_verify_login_flow(self):
        client = APIClient()

        # Register
        res = client.post(reverse('auth_register'), {
            'full_name': 'Test User',
            'email':     'newuser@test.com',
            'password':  'Secure@1234',
        })
        self.assertEqual(res.status_code, 201)

        # OTP get karo
        from jwtapp.models import OTPVerification, User
        user    = User.objects.get(email='newuser@test.com')
        otp_obj = OTPVerification.objects.filter(user=user).last()

        # Verify
        res = client.post(reverse('email_verify'), {
            'email': 'newuser@test.com',
            'otp':   otp_obj.otp,
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn('access', res.data)

        # Login
        res = client.post(reverse('auth_login'), {
            'email': 'newuser@test.com', 'password': 'Secure@1234'
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['role'], 'customer')

    def test_vendor_register_needs_shop_name(self):
        client = APIClient()
        res = client.post(reverse('auth_register'), {
            'full_name': 'Vendor', 'email': 'v@test.com',
            'password': 'Secure@1234', 'role': 'vendor',
        })
        self.assertEqual(res.status_code, 400)

    def test_token_refresh(self):
        user   = UserFactory()
        client = APIClient()
        res    = client.post(reverse('auth_login'), {
            'email': user.email, 'password': 'Secure@1234'
        })
        refresh = res.data['refresh']
        res2 = client.post(reverse('token_refresh'), {'refresh': refresh})
        self.assertEqual(res2.status_code, 200)
        self.assertIn('access', res2.data)

    def test_logout_blacklists_token(self):
        user   = UserFactory()
        client = auth_client(user)
        res    = client.post(reverse('auth_login'), {
            'email': user.email, 'password': 'Secure@1234'
        })
        refresh = res.data['refresh']
        client.post(reverse('auth_logout'), {'refresh': refresh})
        res2 = client.post(reverse('token_refresh'), {'refresh': refresh})
        self.assertEqual(res2.status_code, 401)

    def test_password_change(self):
        user   = UserFactory()
        client = auth_client(user)
        res = client.post(reverse('password_change'), {
            'old_password': 'Secure@1234',
            'new_password': 'NewSecure@5678',
        })
        self.assertEqual(res.status_code, 200)
        # New password se login
        client2 = APIClient()
        res2 = client2.post(reverse('auth_login'), {
            'email': user.email, 'password': 'NewSecure@5678'
        })
        self.assertEqual(res2.status_code, 200)


# ══════════════════════════════════════════════════════════════
# DAY 13 — PRODUCT INTEGRATION TESTS
# ══════════════════════════════════════════════════════════════

class ProductFlowTest(TestCase):

    def setUp(self):
        self.vendor   = VendorFactory()
        self.admin    = AdminFactory()
        self.category = CategoryFactory(name='Electronics')

    def test_vendor_create_product_admin_approve(self):
        v_client = auth_client(self.vendor)
        a_client = auth_client(self.admin, password='Admin@1234')

        # Vendor product banao
        res = v_client.post(reverse('vendor_products'), {
            'name':        'New Phone',
            'description': 'Latest smartphone',
            'price':       '25000.00',
            'category':    str(self.category.pk),
        })
        self.assertEqual(res.status_code, 201)
        product_id = res.data['id']

        # Draft status mein hai
        self.assertEqual(res.data['status'], 'draft')

        # Admin approve kare
        res2 = a_client.patch(
            reverse('admin_product_status', kwargs={'pk': product_id}),
            {'status': 'active'},
            content_type='application/json'
        )
        self.assertEqual(res2.status_code, 200)

        # Public dekh sakta hai ab
        from products.models import Product
        product = Product.objects.get(pk=product_id)
        res3 = APIClient().get(
            reverse('product_detail', kwargs={'slug': product.slug})
        )
        self.assertEqual(res3.status_code, 200)

    def test_product_search_filters(self):
        v = VendorFactory()
        ProductFactory(vendor=v, category=self.category, name='iPhone 15', price=80000, brand='Apple')
        ProductFactory(vendor=v, category=self.category, name='Samsung S24', price=70000, brand='Samsung')
        ProductFactory(vendor=v, category=self.category, name='Budget Phone', price=10000, brand='Xiaomi')

        client = APIClient()

        # Search by name
        res = client.get(reverse('product_search') + '?q=iphone')
        self.assertEqual(res.data['count'], 1)

        # Price filter
        res2 = client.get(reverse('product_search') + '?min_price=50000&max_price=90000')
        self.assertEqual(res2.data['count'], 2)

        # Brand filter
        res3 = client.get(reverse('product_search') + '?brand=Samsung')
        self.assertEqual(res3.data['count'], 1)


# ══════════════════════════════════════════════════════════════
# DAY 13 — CART INTEGRATION TESTS
# ══════════════════════════════════════════════════════════════

class CartFlowTest(TestCase):

    def setUp(self):
        self.user    = UserFactory()
        self.vendor  = VendorFactory()
        self.cat     = CategoryFactory()
        self.product = ProductFactory(vendor=self.vendor, category=self.cat, price=1000)
        self.client  = auth_client(self.user)

    def test_complete_cart_flow(self):
        # Add item
        res = self.client.post(reverse('cart_item_add'), {
            'product_id': str(self.product.pk),
            'quantity':   2,
        })
        self.assertEqual(res.status_code, 201)
        item_id = res.data['id']

        # Check cart total
        res2 = self.client.get(reverse('cart'))
        self.assertEqual(float(res2.data['subtotal']), 2000.0)

        # Apply coupon
        coupon = CouponFactory(discount_type='flat', discount_value=200)
        res3 = self.client.post(reverse('coupon_apply'), {'code': coupon.code})
        self.assertEqual(res3.status_code, 200)
        self.assertEqual(float(res3.data['total']), 1800.0)

        # Remove coupon
        res4 = self.client.delete(reverse('coupon_remove'))
        self.assertEqual(res4.status_code, 200)

        # Update quantity
        res5 = self.client.patch(
            reverse('cart_item_update', kwargs={'pk': item_id}),
            {'quantity': 3}, content_type='application/json'
        )
        self.assertEqual(res5.data['quantity'], 3)

        # Remove item
        res6 = self.client.delete(reverse('cart_item_update', kwargs={'pk': item_id}))
        self.assertEqual(res6.status_code, 204)

    def test_wishlist_to_cart(self):
        # Wishlist mein add karo
        res = self.client.post(reverse('wishlist'), {
            'product_id': str(self.product.pk)
        })
        self.assertEqual(res.status_code, 201)
        wish_id = res.data['id']

        # Cart mein move karo
        res2 = self.client.post(
            reverse('wishlist_move_to_cart', kwargs={'pk': wish_id})
        )
        self.assertEqual(res2.status_code, 200)

        # Wishlist khaali hai ab
        from cart.models import WishlistItem
        self.assertEqual(WishlistItem.objects.count(), 0)

        # Cart mein hai
        from cart.models import CartItem
        self.assertEqual(CartItem.objects.count(), 1)


# ══════════════════════════════════════════════════════════════
# DAY 13 — ORDER INTEGRATION TESTS
# ══════════════════════════════════════════════════════════════

class OrderFlowTest(TestCase):

    def setUp(self):
        self.user    = UserFactory()
        self.vendor  = VendorFactory()
        self.admin   = AdminFactory()
        self.cat     = CategoryFactory()
        self.product = ProductFactory(vendor=self.vendor, category=self.cat, price=500)
        self.address = AddressFactory(user=self.user)
        self.client  = auth_client(self.user)

    def _add_to_cart_and_order(self, quantity=2):
        self.client.post(reverse('cart_item_add'), {
            'product_id': str(self.product.pk),
            'quantity':   quantity,
        })
        res = self.client.post(reverse('order_place'), {
            'address_id': str(self.address.pk)
        })
        return res

    def test_full_order_lifecycle(self):
        res = self._add_to_cart_and_order(quantity=2)
        self.assertEqual(res.status_code, 201)
        order_id = res.data['order_id']

        # Stock check
        self.product.stock.refresh_from_db()
        self.assertEqual(self.product.stock.quantity, 98)

        # Admin order confirm kare
        a_client = auth_client(self.admin, password='Admin@1234')
        a_client.patch(
            reverse('admin_order_status', kwargs={'order_id': order_id}),
            {'status': 'confirmed', 'message': 'Payment received'},
            content_type='application/json'
        )

        # Ship karo
        a_client.patch(
            reverse('admin_order_status', kwargs={'order_id': order_id}),
            {'status': 'shipped', 'message': 'Dispatched', 'location': 'Mumbai'},
            content_type='application/json'
        )

        # Deliver karo
        a_client.patch(
            reverse('admin_order_status', kwargs={'order_id': order_id}),
            {'status': 'delivered', 'message': 'Delivered!'},
            content_type='application/json'
        )

        # Tracking check
        order = Order.objects.get(order_id=order_id)
        self.assertEqual(order.status, 'delivered')
        self.assertEqual(order.tracking.count(), 4)  # pending + confirmed + shipped + delivered

    def test_cancel_restores_stock(self):
        res = self._add_to_cart_and_order(quantity=3)
        order_id = res.data['order_id']

        res2 = self.client.post(
            reverse('order_cancel', kwargs={'order_id': order_id}),
            {'reason': 'Changed mind'}
        )
        self.assertEqual(res2.status_code, 200)
        self.product.stock.refresh_from_db()
        self.assertEqual(self.product.stock.quantity, 100)

    def test_order_tracking_timeline(self):
        res = self._add_to_cart_and_order()
        order_id = res.data['order_id']

        res2 = self.client.get(
            reverse('order_tracking', kwargs={'order_id': order_id})
        )
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(len(res2.data['timeline']), 1)


# ══════════════════════════════════════════════════════════════
# DAY 13 — PAYMENT INTEGRATION TESTS (Mocked)
# ══════════════════════════════════════════════════════════════

class PaymentFlowTest(TestCase):

    def setUp(self):
        self.user    = UserFactory()
        self.vendor  = VendorFactory()
        self.cat     = CategoryFactory()
        self.product = ProductFactory(vendor=self.vendor, category=self.cat, price=999)
        self.address = AddressFactory(user=self.user)
        self.client  = auth_client(self.user)

        # Order banao
        self.client.post(reverse('cart_item_add'), {
            'product_id': str(self.product.pk), 'quantity': 1
        })
        res = self.client.post(reverse('order_place'), {
            'address_id': str(self.address.pk)
        })
        self.order_id = res.data['order_id']

    @patch('payments.views.get_razorpay_client')
    def test_create_razorpay_order(self, mock_rz):
        mock_client = MagicMock()
        mock_client.order.create.return_value = {
            'id':       'order_test123',
            'amount':   99900,
            'currency': 'INR',
        }
        mock_rz.return_value = mock_client

        res = self.client.post(reverse('payment_create'), {
            'order_id': self.order_id
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn('razorpay_order_id', res.data)
        self.assertIn('key', res.data)

    @patch('payments.views.get_razorpay_client')
    def test_verify_payment_success(self, mock_rz):
        mock_client = MagicMock()
        mock_client.order.create.return_value = {'id': 'order_test456', 'amount': 99900, 'currency': 'INR'}
        mock_rz.return_value = mock_client

        self.client.post(reverse('payment_create'), {'order_id': self.order_id})

        # HMAC signature generate karo
        import hmac, hashlib
        from django.conf import settings
        rz_order_id   = 'order_test456'
        rz_payment_id = 'pay_test789'
        body = f"{rz_order_id}|{rz_payment_id}"
        signature = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode(),
            body.encode(),
            hashlib.sha256
        ).hexdigest()

        res = self.client.post(reverse('payment_verify'), {
            'razorpay_order_id':   rz_order_id,
            'razorpay_payment_id': rz_payment_id,
            'razorpay_signature':  signature,
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['status'], 'confirmed')

        order = Order.objects.get(order_id=self.order_id)
        self.assertEqual(order.status, 'confirmed')
        self.assertEqual(order.payment_status, 'paid')


# ══════════════════════════════════════════════════════════════
# DAY 13 — REVIEW INTEGRATION TESTS
# ══════════════════════════════════════════════════════════════

class ReviewFlowTest(TestCase):

    def setUp(self):
        self.user    = UserFactory()
        self.vendor  = VendorFactory()
        self.cat     = CategoryFactory()
        self.product = ProductFactory(vendor=self.vendor, category=self.cat)
        self.client  = auth_client(self.user)

    def test_review_updates_product_rating(self):
        user2 = UserFactory()

        self.client.post(
            reverse('product_reviews', kwargs={'slug': self.product.slug}),
            {'rating': 5, 'body': 'Bahut achha!'}
        )
        auth_client(user2).post(
            reverse('product_reviews', kwargs={'slug': self.product.slug}),
            {'rating': 3, 'body': 'Theek hai'}
        )

        self.product.refresh_from_db()
        self.assertEqual(float(self.product.avg_rating), 4.0)
        self.assertEqual(self.product.total_reviews, 2)

    def test_unverified_user_can_review(self):
        res = self.client.post(
            reverse('product_reviews', kwargs={'slug': self.product.slug}),
            {'rating': 4, 'body': 'Nice product'}
        )
        self.assertEqual(res.status_code, 201)
        self.assertFalse(res.data['is_verified_purchase'])

    def test_vote_toggle(self):
        review  = ReviewFactory(product=self.product)
        voter   = UserFactory()
        vclient = auth_client(voter)

        # Vote karo
        vclient.post(reverse('review_vote', kwargs={'pk': review.pk}), {'vote': 'helpful'})
        review.refresh_from_db()
        self.assertEqual(review.helpful_count, 1)

        # Dobara vote — toggle off
        vclient.post(reverse('review_vote', kwargs={'pk': review.pk}), {'vote': 'helpful'})
        review.refresh_from_db()
        self.assertEqual(review.helpful_count, 0)


# ══════════════════════════════════════════════════════════════
# DAY 13 — PERMISSION TESTS
# ══════════════════════════════════════════════════════════════

class PermissionTest(TestCase):

    def test_customer_cannot_access_admin_endpoints(self):
        user   = UserFactory()
        client = auth_client(user)
        res = client.get(reverse('admin_order_list'))
        self.assertEqual(res.status_code, 403)

    def test_unauthenticated_cannot_place_order(self):
        client = APIClient()
        res = client.post(reverse('order_place'), {'address_id': 'some-id'})
        self.assertEqual(res.status_code, 401)

    def test_vendor_cannot_see_others_products(self):
        v1 = VendorFactory()
        v2 = VendorFactory()
        from products.models import Product, Category
        cat = CategoryFactory()
        p   = Product.objects.create(
            vendor=v2, category=cat, name='V2 Product',
            description='d', price=100
        )
        client = auth_client(v1)
        res = client.get(reverse('vendor_product_detail', kwargs={'pk': p.pk}))
        self.assertEqual(res.status_code, 404)

    def test_customer_cannot_access_vendor_dashboard(self):
        user   = UserFactory(role='customer')
        client = auth_client(user)
        res = client.get(reverse('vendor_dashboard'))
        self.assertEqual(res.status_code, 403)
