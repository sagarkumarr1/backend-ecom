import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from jwtapp.models import User
from products.models import Product


class Review(models.Model):
    """
    Sirf woh customer review kar sakta hai jisne product order kiya ho
    aur deliver bhi hua ho — verified purchase.
    """
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product    = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')

    rating     = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title      = models.CharField(max_length=200, blank=True)
    body       = models.TextField()
    images     = models.JSONField(default=list, blank=True)  # List of image URLs

    is_verified_purchase = models.BooleanField(default=False)
    is_approved          = models.BooleanField(default=True)  # Admin moderate kar sakta hai

    helpful_count    = models.PositiveIntegerField(default=0)
    not_helpful_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table        = 'reviews'
        unique_together = ('product', 'user')  # Ek user ek product pe sirf ek review
        ordering        = ['-created_at']

    def __str__(self):
        return f"{self.product.name} — {self.user.email} ({self.rating}★)"


class ReviewVote(models.Model):
    """
    Helpful / Not Helpful vote on a review.
    """
    class VoteType(models.TextChoices):
        HELPFUL     = 'helpful',     'Helpful'
        NOT_HELPFUL = 'not_helpful', 'Not Helpful'

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    review     = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='votes')
    user       = models.ForeignKey(User, on_delete=models.CASCADE)
    vote       = models.CharField(max_length=15, choices=VoteType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table        = 'review_votes'
        unique_together = ('review', 'user')

    def __str__(self):
        return f"{self.user.email} — {self.vote} on {self.review}"
