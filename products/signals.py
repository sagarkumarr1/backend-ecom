"""
products/signals.py
Review save hone ke baad product ka avg_rating aur total_reviews
automatically update hoga — koi manual kaam nahi.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Avg


def update_product_rating(product):
    """Product ka avg rating aur review count recalculate karo."""
    # Import yahan karo — circular import avoid karne ke liye
    from django.apps import apps
    Review = apps.get_model('reviews', 'Review')

    result = Review.objects.filter(
        product=product, is_approved=True
    ).aggregate(avg=Avg('rating'))

    product.avg_rating    = result['avg'] or 0.00
    product.total_reviews = Review.objects.filter(product=product, is_approved=True).count()
    product.save(update_fields=['avg_rating', 'total_reviews'])
