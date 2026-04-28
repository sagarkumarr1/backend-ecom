from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from .models import User, Address, OTPVerification


class AuthTests(TestCase):
    """Day 2 — Auth API tests"""

    def setUp(self):
        self.client = APIClient()
        self.register_url       = reverse('auth_register')
        self.login_url          = reverse('auth_login')
        self.verify_url         = reverse('email_verify')

    def test_register_customer(self):
        res = self.client.post(self.register_url, {
            'full_name': 'Test User',
            'email':     'test@example.com',
            'password':  'Secure@1234',
        })
        self.assertEqual(res.status_code, 201)
        self.assertEqual(User.objects.count(), 1)

    def test_register_vendor_without_shop_name_fails(self):
        res = self.client.post(self.register_url, {
            'full_name': 'Vendor User',
            'email':     'vendor@example.com',
            'password':  'Secure@1234',
            'role':      'vendor',
        })
        self.assertEqual(res.status_code, 400)

    def test_login(self):
        User.objects.create_user(
            email='login@example.com', full_name='Login User',
            password='Secure@1234', is_email_verified=True
        )
        res = self.client.post(self.login_url, {
            'email': 'login@example.com', 'password': 'Secure@1234'
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn('access', res.data)
        self.assertIn('refresh', res.data)

    def test_email_verify(self):
        user = User.objects.create_user(
            email='verify@example.com', full_name='Verify User', password='Secure@1234'
        )
        otp_obj = OTPVerification.create_otp(user, OTPVerification.PURPOSE_EMAIL_VERIFY)
        res = self.client.post(self.verify_url, {'email': user.email, 'otp': otp_obj.otp})
        self.assertEqual(res.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)


class AddressTests(TestCase):
    """Day 1 — Address API tests"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='addr@example.com', full_name='Addr User',
            password='Secure@1234', is_email_verified=True
        )
        # Login karke token lo
        res = self.client.post(reverse('auth_login'), {
            'email': 'addr@example.com', 'password': 'Secure@1234'
        })
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

    def _address_data(self, is_default=False):
        return {
            'full_name':     'Test User',
            'phone':         '9876543210',
            'address_line1': '123 Main St',
            'city':          'Mumbai',
            'state':         'Maharashtra',
            'pincode':       '400001',
            'address_type':  'home',
            'is_default':    is_default,
        }

    def test_create_address(self):
        res = self.client.post(reverse('address_list'), self._address_data())
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Address.objects.filter(user=self.user).count(), 1)

    def test_only_one_default_address(self):
        self.client.post(reverse('address_list'), self._address_data(is_default=True))
        self.client.post(reverse('address_list'), {**self._address_data(is_default=True), 'city': 'Delhi', 'state': 'Delhi'})
        self.assertEqual(Address.objects.filter(user=self.user, is_default=True).count(), 1)

    def test_invalid_pincode_fails(self):
        data = self._address_data()
        data['pincode'] = '12345'  # 5 digits — galat
        res = self.client.post(reverse('address_list'), data)
        self.assertEqual(res.status_code, 400)

    def test_cannot_access_others_address(self):
        other_user = User.objects.create_user(
            email='other@example.com', full_name='Other', password='Secure@1234'
        )
        addr = Address.objects.create(
            user=other_user, full_name='Other', phone='9999999999',
            address_line1='XYZ', city='Pune', state='MH', pincode='411001'
        )
        res = self.client.get(reverse('address_detail', kwargs={'pk': addr.pk}))
        self.assertEqual(res.status_code, 404)


class AdminTests(TestCase):
    """Day 3 — Admin panel tests"""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email='admin@example.com', full_name='Admin', password='Admin@1234'
        )
        res = self.client.post(reverse('auth_login'), {
            'email': 'admin@example.com', 'password': 'Admin@1234'
        })
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

    def test_admin_dashboard(self):
        res = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(res.status_code, 200)
        self.assertIn('total_users', res.data)

    def test_vendor_approve(self):
        vendor = User.objects.create_user(
            email='v@example.com', full_name='Vendor', password='Secure@1234',
            role='vendor', shop_name='My Shop'
        )
        res = self.client.patch(
            reverse('vendor_approve', kwargs={'pk': vendor.pk}),
            {'is_vendor_approved': True},
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        vendor.refresh_from_db()
        self.assertTrue(vendor.is_vendor_approved)
