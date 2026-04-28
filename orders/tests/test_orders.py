from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from jwtapp.models import User, Address
from products.models import Category, Product, Stock
from cart.models import Cart, CartItem
from orders.models import Order, OrderItem


def make_customer():
    return User.objects.create_user(
        email='customer@test.com', full_name='Test Customer',
        password='Secure@1234', is_email_verified=True
    )

def make_vendor():
    return User.objects.create_user(
        email='vendor@test.com', full_name='Vendor',
        password='Secure@1234', role='vendor',
        shop_name='Shop', is_email_verified=True, is_vendor_approved=True
    )

def make_admin():
    return User.objects.create_superuser(
        email='admin@test.com', full_name='Admin', password='Admin@1234'
    )

def get_token(client, email, password='Secure@1234'):
    res = client.post(reverse('auth_login'), {'email': email, 'password': password})
    return res.data['access']

def make_product(vendor, category, price=1000):
    p = Product.objects.create(
        vendor=vendor, category=category,
        name='Test Product', description='desc',
        price=price, status='active'
    )
    Stock.objects.create(product=p, quantity=50)
    return p

def make_address(user):
    return Address.objects.create(
        user=user, full_name='Test User', phone='9876543210',
        address_line1='123 Street', city='Mumbai',
        state='Maharashtra', pincode='400001', is_default=True
    )


class PlaceOrderTests(TestCase):

    def setUp(self):
        self.client   = APIClient()
        self.customer = make_customer()
        self.vendor   = make_vendor()
        self.category = Category.objects.create(name='Electronics')
        self.product  = make_product(self.vendor, self.category)
        self.address  = make_address(self.customer)

        token = get_token(self.client, 'customer@test.com')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # Add item to cart
        self.client.post(reverse('cart_item_add'), {
            'product_id': str(self.product.pk), 'quantity': 2
        })

    def test_place_order_success(self):
        res = self.client.post(reverse('order_place'), {
            'address_id': str(self.address.pk)
        })
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.data['order_id'].startswith('ORD-'))
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderItem.objects.count(), 1)

    def test_stock_deducted_after_order(self):
        self.client.post(reverse('order_place'), {
            'address_id': str(self.address.pk)
        })
        self.product.stock.refresh_from_db()
        self.assertEqual(self.product.stock.quantity, 48)  # 50 - 2

    def test_cart_cleared_after_order(self):
        self.client.post(reverse('order_place'), {
            'address_id': str(self.address.pk)
        })
        self.assertEqual(CartItem.objects.count(), 0)

    def test_empty_cart_order_fails(self):
        # Clear cart first
        self.client.delete(reverse('cart'))
        res = self.client.post(reverse('order_place'), {
            'address_id': str(self.address.pk)
        })
        self.assertEqual(res.status_code, 400)

    def test_invalid_address_fails(self):
        import uuid
        res = self.client.post(reverse('order_place'), {
            'address_id': str(uuid.uuid4())
        })
        self.assertEqual(res.status_code, 400)


class CancelOrderTests(TestCase):

    def setUp(self):
        self.client   = APIClient()
        self.customer = make_customer()
        self.vendor   = make_vendor()
        self.category = Category.objects.create(name='Fashion')
        self.product  = make_product(self.vendor, self.category)
        self.address  = make_address(self.customer)

        token = get_token(self.client, 'customer@test.com')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        self.client.post(reverse('cart_item_add'), {
            'product_id': str(self.product.pk), 'quantity': 3
        })
        res = self.client.post(reverse('order_place'), {
            'address_id': str(self.address.pk)
        })
        self.order_id = res.data['order_id']

    def test_cancel_pending_order(self):
        res = self.client.post(
            reverse('order_cancel', kwargs={'order_id': self.order_id}),
            {'reason': 'Changed my mind'}
        )
        self.assertEqual(res.status_code, 200)
        order = Order.objects.get(order_id=self.order_id)
        self.assertEqual(order.status, 'cancelled')

    def test_stock_restored_after_cancel(self):
        self.client.post(
            reverse('order_cancel', kwargs={'order_id': self.order_id}),
            {'reason': 'Test'}
        )
        self.product.stock.refresh_from_db()
        self.assertEqual(self.product.stock.quantity, 50)  # Restored

    def test_cancel_delivered_order_fails(self):
        order = Order.objects.get(order_id=self.order_id)
        order.status = 'delivered'
        order.save()
        res = self.client.post(
            reverse('order_cancel', kwargs={'order_id': self.order_id}),
            {}
        )
        self.assertEqual(res.status_code, 400)


class AdminOrderTests(TestCase):

    def setUp(self):
        self.client   = APIClient()
        self.admin    = make_admin()
        self.customer = make_customer()
        self.vendor   = make_vendor()
        self.category = Category.objects.create(name='Books')
        self.product  = make_product(self.vendor, self.category)
        self.address  = make_address(self.customer)

        # Customer se order place karwao
        cust_client = APIClient()
        token = get_token(cust_client, 'customer@test.com')
        cust_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        cust_client.post(reverse('cart_item_add'), {
            'product_id': str(self.product.pk), 'quantity': 1
        })
        res = cust_client.post(reverse('order_place'), {
            'address_id': str(self.address.pk)
        })
        self.order_id = res.data['order_id']

        # Admin login
        token = get_token(self.client, 'admin@test.com', 'Admin@1234')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_admin_list_orders(self):
        res = self.client.get(reverse('admin_order_list'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['count'], 1)

    def test_admin_update_order_status(self):
        res = self.client.patch(
            reverse('admin_order_status', kwargs={'order_id': self.order_id}),
            {'status': 'confirmed', 'message': 'Payment received'},
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        order = Order.objects.get(order_id=self.order_id)
        self.assertEqual(order.status, 'confirmed')
        self.assertEqual(order.payment_status, 'paid')

    def test_tracking_entry_created(self):
        self.client.patch(
            reverse('admin_order_status', kwargs={'order_id': self.order_id}),
            {'status': 'shipped', 'message': 'Dispatched', 'location': 'Mumbai'},
            content_type='application/json'
        )
        order = Order.objects.get(order_id=self.order_id)
        self.assertTrue(order.tracking.filter(status='shipped').exists())
