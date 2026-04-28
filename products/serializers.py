from rest_framework import serializers
from .models import Category, Product, ProductImage, ProductVariant, Stock


# ─── Category ─────────────────────────────────────────────────────────────
class CategorySerializer(serializers.ModelSerializer):
    children_count = serializers.SerializerMethodField()
    products_count = serializers.SerializerMethodField()

    class Meta:
        model  = Category
        fields = (
            'id', 'name', 'slug', 'description', 'image',
            'parent', 'is_active', 'children_count', 'products_count'
        )
        read_only_fields = ('id', 'slug')

    def get_children_count(self, obj):
        return obj.children.filter(is_active=True).count()

    def get_products_count(self, obj):
        return obj.products.filter(status='active').count()


class CategoryTreeSerializer(serializers.ModelSerializer):
    """Nested children ke saath — tree view ke liye."""
    children = serializers.SerializerMethodField()

    class Meta:
        model  = Category
        fields = ('id', 'name', 'slug', 'image', 'children')

    def get_children(self, obj):
        return CategoryTreeSerializer(
            obj.children.filter(is_active=True), many=True
        ).data


# ─── Product Image ────────────────────────────────────────────────────────
class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ProductImage
        fields = ('id', 'image_url', 'alt_text', 'is_primary', 'order')
        read_only_fields = ('id',)


# ─── Product Variant ──────────────────────────────────────────────────────
class ProductVariantSerializer(serializers.ModelSerializer):
    final_price  = serializers.ReadOnlyField()
    is_in_stock  = serializers.ReadOnlyField()

    class Meta:
        model  = ProductVariant
        fields = (
            'id', 'name', 'size', 'color', 'extra_price',
            'stock', 'sku', 'image_url', 'is_active',
            'final_price', 'is_in_stock',
        )
        read_only_fields = ('id', 'sku')


# ─── Stock ────────────────────────────────────────────────────────────────
class StockSerializer(serializers.ModelSerializer):
    is_low_stock    = serializers.ReadOnlyField()
    is_out_of_stock = serializers.ReadOnlyField()

    class Meta:
        model  = Stock
        fields = ('quantity', 'low_stock_threshold', 'is_low_stock', 'is_out_of_stock', 'updated_at')
        read_only_fields = ('updated_at',)


# ─── Product List (lightweight — listing page ke liye) ────────────────────
class ProductListSerializer(serializers.ModelSerializer):
    primary_image    = serializers.SerializerMethodField()
    category_name    = serializers.CharField(source='category.name', read_only=True)
    discounted_price = serializers.ReadOnlyField()
    is_in_stock      = serializers.ReadOnlyField()
    vendor_name      = serializers.CharField(source='vendor.full_name', read_only=True)

    class Meta:
        model  = Product
        fields = (
            'id', 'name', 'slug', 'price', 'discount_percent',
            'discounted_price', 'brand', 'category_name',
            'avg_rating', 'total_reviews', 'total_sold',
            'is_featured', 'is_in_stock', 'primary_image',
            'vendor_name', 'status',
        )

    def get_primary_image(self, obj):
        img = obj.images.filter(is_primary=True).first() or obj.images.first()
        return img.image_url if img else None


# ─── Product Detail (full — product page ke liye) ─────────────────────────
class ProductDetailSerializer(serializers.ModelSerializer):
    images           = ProductImageSerializer(many=True, read_only=True)
    variants         = ProductVariantSerializer(many=True, read_only=True)
    stock            = StockSerializer(read_only=True)
    category         = CategorySerializer(read_only=True)
    discounted_price = serializers.ReadOnlyField()
    is_in_stock      = serializers.ReadOnlyField()
    vendor_name      = serializers.CharField(source='vendor.full_name', read_only=True)
    vendor_shop      = serializers.CharField(source='vendor.shop_name', read_only=True)

    class Meta:
        model  = Product
        fields = (
            'id', 'name', 'slug', 'description', 'price',
            'discount_percent', 'discounted_price', 'brand', 'sku',
            'category', 'status', 'is_featured', 'is_in_stock',
            'avg_rating', 'total_reviews', 'total_sold',
            'images', 'variants', 'stock',
            'vendor_name', 'vendor_shop',
            'created_at', 'updated_at',
        )


# ─── Product Create/Update (Vendor use karega) ────────────────────────────
class ProductWriteSerializer(serializers.ModelSerializer):
    """
    Vendor naya product banane ke liye.
    Images aur variants alag endpoints se add honge.
    """
    class Meta:
        model  = Product
        fields = (
            'name', 'description', 'price', 'discount_percent',
            'brand', 'category', 'is_featured',
        )

    def validate_discount_percent(self, value):
        if not (0 <= value <= 90):
            raise serializers.ValidationError("Discount 0 se 90 ke beech hona chahiye.")
        return value

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price 0 se zyada honi chahiye.")
        return value

    def create(self, validated_data):
        vendor = self.context['request'].user
        product = Product.objects.create(vendor=vendor, **validated_data)
        # Default stock entry banao
        Stock.objects.create(product=product, quantity=0)
        return product


# ─── Admin Product Serializer ─────────────────────────────────────────────
class AdminProductSerializer(serializers.ModelSerializer):
    """Admin product approve/reject/feature kar sakta hai."""
    class Meta:
        model  = Product
        fields = ('id', 'name', 'status', 'is_featured', 'vendor', 'created_at')
        read_only_fields = ('id', 'name', 'vendor', 'created_at')
