from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from jwtapp.models import User
from products.models import Category, Product, Stock
from reviews.models import Review, ReviewVote


def make_user(email='user@test.com'):
    return User.objects.create_user(
        email=email, full_name='Test User',
        password='Secure@1234', is_email_verified=True
    )

def make_vendor():
    return User.objects.create_user(
        email='vendor@test.com', full_name='Vendor',
        password='Secure@1234', role='vendor',
        shop_name='Shop', is_email_verified=True, is_vendor_approved=True
    )

def make_product(vendor):
    cat = Category.objects.create(name='Electronics')
    p   = Product.objects.create(
        vendor=vendor, category=cat,
        name='Test Product', description='desc',
        price=999, status='active'
    )
    Stock.objects.create(product=p, quantity=10)
    return p

def get_token(client, email, password='Secure@1234'):
    res = client.post(reverse('auth_login'), {'email': email, 'password': password})
    return res.data['access']


class ReviewTests(TestCase):

    def setUp(self):
        self.client  = APIClient()
        self.user    = make_user()
        self.vendor  = make_vendor()
        self.product = make_product(self.vendor)
        token = get_token(self.client, 'user@test.com')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_list_reviews_public(self):
        Review.objects.create(
            product=self.product, user=self.user,
            rating=4, body='Achha product hai'
        )
        self.client.credentials()
        res = self.client.get(
            reverse('product_reviews', kwargs={'slug': self.product.slug})
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn('summary', res.data)
        self.assertEqual(len(res.data['reviews']), 1)

    def test_write_review(self):
        token = get_token(self.client, 'user@test.com')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        res = self.client.post(
            reverse('product_reviews', kwargs={'slug': self.product.slug}),
            {'rating': 5, 'title': 'Zabardast', 'body': 'Bahut achha product'}
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Review.objects.count(), 1)

    def test_duplicate_review_fails(self):
        Review.objects.create(
            product=self.product, user=self.user,
            rating=3, body='Ok product'
        )
        res = self.client.post(
            reverse('product_reviews', kwargs={'slug': self.product.slug}),
            {'rating': 4, 'body': 'Changed mind'}
        )
        self.assertEqual(res.status_code, 400)

    def test_avg_rating_updated(self):
        user2 = make_user('user2@test.com')
        Review.objects.create(product=self.product, user=self.user, rating=4, body='Good')
        Review.objects.create(product=self.product, user=user2, rating=2, body='Ok')

        # Manually update rating (signal ya direct)
        from reviews.views import _update_product_rating
        _update_product_rating(self.product)

        self.product.refresh_from_db()
        self.assertEqual(float(self.product.avg_rating), 3.0)

    def test_helpful_vote(self):
        review = Review.objects.create(
            product=self.product, user=self.user,
            rating=5, body='Great!'
        )
        user2  = make_user('voter@test.com')
        token2 = get_token(self.client, 'voter@test.com')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token2}')

        res = self.client.post(
            reverse('review_vote', kwargs={'pk': review.pk}),
            {'vote': 'helpful'}
        )
        self.assertEqual(res.status_code, 200)
        review.refresh_from_db()
        self.assertEqual(review.helpful_count, 1)

    def test_invalid_rating_fails(self):
        res = self.client.post(
            reverse('product_reviews', kwargs={'slug': self.product.slug}),
            {'rating': 6, 'body': 'Too good'}
        )
        self.assertEqual(res.status_code, 400)
