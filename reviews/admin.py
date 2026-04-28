from django.contrib import admin
from .models import Review, ReviewVote

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display  = ('product', 'user', 'rating', 'is_approved', 'is_verified_purchase', 'created_at')
    list_filter   = ('is_approved', 'rating', 'is_verified_purchase')
    search_fields = ('product__name', 'user__email')
    actions       = ['approve_reviews', 'unapprove_reviews']

    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
    approve_reviews.short_description = "Approve karo"

    def unapprove_reviews(self, request, queryset):
        queryset.update(is_approved=False)
    unapprove_reviews.short_description = "Unapprove karo"
