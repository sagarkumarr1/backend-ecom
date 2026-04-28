from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from jwtapp.models import User
from products.models import Category, Product, Stock
from cart.models import Cart, CartItem, Coupon, WishlistItem


def make_user(email='user@test.com'):
    return User.objects.create_user(
        email=email, full_name='Test User',
        password='Secure@1234', is_email_verified=True
    )


def make_product(vendor, category, name='Test Product', price=1000):
    p = Product.objects.create(
        vendor=vendor, category=category,
        name=name, description='desc', price=price, status='active'
    )
    Stock.objects.create(product=p, quantity=50)
    return p


def make_vendor():
    return User.objects.create_user(
        email='vendor@test.com', full_name='Vendor',
        password='Secure@1234', role='vendor',
        shop_name='Shop', is_email_verified=True, is_vendor_approved=True
    )


def get_token(client, email, password='Secure@1234'):
    res = client.post(reverse('auth_login'), {'email': email, 'password': password})
    return res.data['access']


class CartTests(TestCase):

    def setUp(self):
        self.client   = APIClient()
        self.user     = make_user()
        self.vendor   = make_vendor()
        self.category = Category.objects.create(name='Electronics')
        self.product  = make_product(self.vendor, self.category)
        token = get_token(self.client, 'user@test.com')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_get_cart_creates_empty_cart(self):
        res = self.client.get(reverse('cart'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['total_items'], 0)

    def test_add_item_to_cart(self):
        res = self.client.post(reverse('cart_item_add'), {
            'product_id': str(self.product.pk),
            'quantity':   2,
        })
        self.assertEqual(res.status_code, 201)
        self.assertEqual(CartItem.objects.count(), 1)

    def test_add_same_item_increases_quantity(self):
        self.client.post(reverse('cart_item_add'), {
            'product_id': str(self.product.pk), 'quantity': 2
        })
        self.client.post(reverse('cart_item_add'), {
            'product_id': str(self.product.pk), 'quantity': 3
        })
        item = CartItem.objects.get(cart__user=self.user)
        self.assertEqual(item.quantity, 5)

    def test_cart_total_calculation(self):
        self.client.post(reverse('cart_item_add'), {
            'product_id': str(self.product.pk), 'quantity': 2
        })
        res = self.client.get(reverse('cart'))
        self.assertEqual(float(res.data['subtotal']), 2000.0)
        self.assertEqual(float(res.data['total']), 2000.0)

    def test_clear_cart(self):
        self.client.post(reverse('cart_item_add'), {
            'product_id': str(self.product.pk), 'quantity': 1
        })
        res = self.client.delete(reverse('cart'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(CartItem.objects.count(), 0)

    def test_update_item_quantity(self):
        res = self.client.post(reverse('cart_item_add'), {
            'product_id': str(self.product.pk), 'quantity': 1
        })
        item_id = res.data['id']
        res = self.client.patch(
            reverse('cart_item_update', kwargs={'pk': item_id}),
            {'quantity': 5}, content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['quantity'], 5)

    def test_remove_item(self):
        res = self.client.post(reverse('cart_item_add'), {
            'product_id': str(self.product.pk), 'quantity': 1
        })
        item_id = res.data['id']
        res = self.client.delete(reverse('cart_item_update', kwargs={'pk': item_id}))
        self.assertEqual(res.status_code, 204)
        self.assertEqual(CartItem.objects.count(), 0)


class CouponTests(TestCase):

    def setUp(self):
        self.client  = APIClient()
        self.user    = make_user()
        self.vendor  = make_vendor()
        self.cat     = Category.objects.create(name='Fashion')
        self.product = make_product(self.vendor, self.cat, price=1000)
        token = get_token(self.client, 'user@test.com')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        # Add item to cart
        self.client.post(reverse('cart_item_add'), {
            'product_id': str(self.product.pk), 'quantity': 2
        })

    def test_apply_flat_coupon(self):
        coupon = Coupon.objects.create(
            code='SAVE200', discount_type='flat',
            discount_value=200, usage_limit=10
        )
        res = self.client.post(reverse('coupon_apply'), {'code': 'SAVE200'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(float(res.data['discount_amount']), 200.0)
        self.assertEqual(float(res.data['total']), 1800.0)

    def test_apply_percentage_coupon(self):
        coupon = Coupon.objects.create(
            code='SUMMER10', discount_type='percentage',
            discount_value=10, usage_limit=10
        )
        res = self.client.post(reverse('coupon_apply'), {'code': 'SUMMER10'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(float(res.data['discount_amount']), 200.0)

    def test_invalid_coupon_fails(self):
        res = self.client.post(reverse('coupon_apply'), {'code': 'INVALID'})
        self.assertEqual(res.status_code, 400)

    def test_min_order_amount_check(self):
        coupon = Coupon.objects.create(
            code='BIGSAVE', discount_type='flat',
            discount_value=500, min_order_amount=5000, usage_limit=10
        )
        res = self.client.post(reverse('coupon_apply'), {'code': 'BIGSAVE'})
        self.assertEqual(res.status_code, 400)

    def test_remove_coupon(self):
        Coupon.objects.create(code='TEST50', discount_type='flat', discount_value=50, usage_limit=10)
        self.client.post(reverse('coupon_apply'), {'code': 'TEST50'})
        res = self.client.delete(reverse('coupon_remove'))
        self.assertEqual(res.status_code, 200)


class WishlistTests(TestCase):

    def setUp(self):
        self.client  = APIClient()
        self.user    = make_user()
        self.vendor  = make_vendor()
        self.cat     = Category.objects.create(name='Books')
        self.product = make_product(self.vendor, self.cat)
        token = get_token(self.client, 'user@test.com')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_add_to_wishlist(self):
        res = self.client.post(reverse('wishlist'), {'product_id': str(self.product.pk)})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(WishlistItem.objects.count(), 1)

    def test_no_duplicate_wishlist(self):
        self.client.post(reverse('wishlist'), {'product_id': str(self.product.pk)})
        res = self.client.post(reverse('wishlist'), {'product_id': str(self.product.pk)})
        self.assertEqual(res.status_code, 200)  # Already exists message
        self.assertEqual(WishlistItem.objects.count(), 1)

    def test_move_to_cart(self):
        res = self.client.post(reverse('wishlist'), {'product_id': str(self.product.pk)})
        wish_id = res.data['id']
        res = self.client.post(reverse('wishlist_move_to_cart', kwargs={'pk': wish_id}))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(WishlistItem.objects.count(), 0)
        self.assertEqual(CartItem.objects.count(), 1)
