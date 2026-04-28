from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from jwtapp.models import User
from products.models import Category, Product, Stock


def make_vendor(email='vendor@test.com'):
    return User.objects.create_user(
        email=email, full_name='Test Vendor', password='Secure@1234',
        role='vendor', shop_name='Test Shop',
        is_email_verified=True, is_vendor_approved=True
    )


def make_admin():
    return User.objects.create_superuser(
        email='admin@test.com', full_name='Admin', password='Admin@1234'
    )


def get_token(client, email, password):
    res = client.post(reverse('auth_login'), {'email': email, 'password': password})
    return res.data['access']


class CategoryTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.cat = Category.objects.create(name='Electronics', description='Gadgets')

    def test_category_list_public(self):
        res = self.client.get(reverse('category_list'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)

    def test_category_tree(self):
        child = Category.objects.create(name='Phones', parent=self.cat)
        res = self.client.get(reverse('category_tree'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data[0]['children'][0]['name'], 'Phones')

    def test_slug_auto_generated(self):
        self.assertEqual(self.cat.slug, 'electronics')


class ProductTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.vendor = make_vendor()
        self.category = Category.objects.create(name='Electronics')
        token = get_token(self.client, 'vendor@test.com', 'Secure@1234')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_vendor_create_product(self):
        res = self.client.post(reverse('vendor_products'), {
            'name':        'iPhone 15',
            'description': 'Latest Apple phone',
            'price':       '79999.00',
            'category':    str(self.category.pk),
        })
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Product.objects.count(), 1)
        # Stock entry auto bani?
        self.assertTrue(Stock.objects.filter(product__name='iPhone 15').exists())

    def test_product_slug_auto_generated(self):
        product = Product.objects.create(
            vendor=self.vendor, category=self.category,
            name='Test Product', description='desc', price=100
        )
        self.assertIn('test-product', product.slug)

    def test_product_sku_auto_generated(self):
        product = Product.objects.create(
            vendor=self.vendor, category=self.category,
            name='SKU Test', description='desc', price=100
        )
        self.assertTrue(product.sku.startswith('SKU-'))

    def test_discounted_price(self):
        product = Product.objects.create(
            vendor=self.vendor, category=self.category,
            name='Discounted', description='desc',
            price=1000, discount_percent=10
        )
        self.assertEqual(float(product.discounted_price), 900.0)

    def test_public_sees_only_active_products(self):
        # Draft product
        Product.objects.create(
            vendor=self.vendor, category=self.category,
            name='Draft', description='d', price=100, status='draft'
        )
        # Active product
        Product.objects.create(
            vendor=self.vendor, category=self.category,
            name='Active', description='a', price=100, status='active'
        )
        self.client.credentials()  # no token — public
        res = self.client.get(reverse('product_list'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['count'] if isinstance(res.data, dict) else len(res.data), 1)

    def test_invalid_discount_fails(self):
        res = self.client.post(reverse('vendor_products'), {
            'name':             'Bad Discount',
            'description':      'desc',
            'price':            '100.00',
            'category':         str(self.category.pk),
            'discount_percent': 95,   # 90 se zyada — galat
        })
        self.assertEqual(res.status_code, 400)

    def test_vendor_cannot_see_others_products(self):
        other_vendor = make_vendor(email='other@test.com')
        product = Product.objects.create(
            vendor=other_vendor, category=self.category,
            name='Other Product', description='d', price=100
        )
        res = self.client.get(reverse('vendor_product_detail', kwargs={'pk': product.pk}))
        self.assertEqual(res.status_code, 404)


class AdminProductTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin  = make_admin()
        self.vendor = make_vendor()
        self.cat    = Category.objects.create(name='Fashion')
        token = get_token(self.client, 'admin@test.com', 'Admin@1234')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_admin_can_approve_product(self):
        product = Product.objects.create(
            vendor=self.vendor, category=self.cat,
            name='Approve Me', description='d', price=500, status='draft'
        )
        res = self.client.patch(
            reverse('admin_product_status', kwargs={'pk': product.pk}),
            {'status': 'active'}, content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        product.refresh_from_db()
        self.assertEqual(product.status, 'active')

    def test_admin_create_category(self):
        res = self.client.post(reverse('admin_category_create'), {
            'name': 'New Category', 'description': 'Test'
        })
        self.assertEqual(res.status_code, 201)
