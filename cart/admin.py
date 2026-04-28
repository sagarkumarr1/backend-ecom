from django.contrib import admin
from .models import Cart, CartItem, WishlistItem, Coupon


class CartItemInline(admin.TabularInline):
    model  = CartItem
    extra  = 0
    fields = ('product', 'variant', 'quantity')
    readonly_fields = ('product', 'variant')


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display  = ('user', 'total_items', 'coupon', 'updated_at')
    search_fields = ('user__email',)
    inlines       = [CartItemInline]
    readonly_fields = ('created_at', 'updated_at')

    def total_items(self, obj):
        return obj.total_items
    total_items.short_description = 'Items'


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display  = ('code', 'discount_type', 'discount_value', 'used_count', 'usage_limit', 'is_active', 'valid_until')
    list_filter   = ('discount_type', 'is_active')
    search_fields = ('code',)
    readonly_fields = ('used_count', 'created_at')


@admin.register(WishlistItem)
class WishlistAdmin(admin.ModelAdmin):
    list_display  = ('user', 'product', 'added_at')
    search_fields = ('user__email', 'product__name')
