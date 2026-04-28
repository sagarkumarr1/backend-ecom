from django.contrib import admin
from .models import Category, Product, ProductImage, ProductVariant, Stock


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ('name', 'parent', 'is_active', 'created_at')
    list_filter   = ('is_active', 'parent')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)


class ProductImageInline(admin.TabularInline):
    model  = ProductImage
    extra  = 1
    fields = ('image_url', 'alt_text', 'is_primary', 'order')


class ProductVariantInline(admin.TabularInline):
    model  = ProductVariant
    extra  = 1
    fields = ('name', 'size', 'color', 'stock', 'extra_price', 'is_active')


class StockInline(admin.StackedInline):
    model  = Stock
    fields = ('quantity', 'low_stock_threshold')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display   = ('name', 'vendor', 'category', 'price', 'status', 'is_featured', 'avg_rating', 'total_sold')
    list_filter    = ('status', 'is_featured', 'category')
    search_fields  = ('name', 'brand', 'sku', 'vendor__email')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('avg_rating', 'total_reviews', 'total_sold', 'sku', 'created_at', 'updated_at')
    inlines        = [ProductImageInline, ProductVariantInline, StockInline]
    ordering       = ('-created_at',)

    actions = ['make_active', 'make_inactive', 'make_featured', 'remove_featured']

    def make_active(self, request, queryset):
        queryset.update(status='active')
    make_active.short_description = "Selected products Active karo"

    def make_inactive(self, request, queryset):
        queryset.update(status='inactive')
    make_inactive.short_description = "Selected products Inactive karo"

    def make_featured(self, request, queryset):
        queryset.update(is_featured=True)
    make_featured.short_description = "Selected products Featured karo"

    def remove_featured(self, request, queryset):
        queryset.update(is_featured=False)
    remove_featured.short_description = "Featured se remove karo"


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display  = ('product', 'name', 'size', 'color', 'stock', 'extra_price', 'is_active')
    list_filter   = ('is_active',)
    search_fields = ('product__name', 'name', 'sku')


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display  = ('product', 'quantity', 'low_stock_threshold', 'is_low_stock', 'updated_at')
    search_fields = ('product__name',)
    readonly_fields = ('updated_at',)

    def is_low_stock(self, obj):
        return obj.is_low_stock
    is_low_stock.boolean = True
    is_low_stock.short_description = 'Low Stock?'
