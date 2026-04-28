from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status, generics, filters
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .models import Category, Product, ProductImage, ProductVariant, Stock
from .serializers import (
    CategorySerializer, CategoryTreeSerializer,
    ProductListSerializer, ProductDetailSerializer,
    ProductWriteSerializer, AdminProductSerializer,
    ProductImageSerializer, ProductVariantSerializer, StockSerializer,
)
from .filters import ProductFilter
from jwtapp.permissions import IsAdminUser, IsVendorUser, IsVendorOrAdmin


# ══════════════════════════════════════════════════════════════
# CATEGORY VIEWS — Public
# ══════════════════════════════════════════════════════════════

class CategoryListView(APIView):
    """
    GET /api/products/categories/        — flat list
    GET /api/products/categories/tree/   — nested tree
    """
    permission_classes = [AllowAny]

    def get(self, request):
        categories = Category.objects.filter(is_active=True, parent=None)
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)


class CategoryTreeView(APIView):
    """Category tree — parent > children nested."""
    permission_classes = [AllowAny]

    def get(self, request):
        root_categories = Category.objects.filter(is_active=True, parent=None)
        return Response(CategoryTreeSerializer(root_categories, many=True).data)


class CategoryDetailView(APIView):
    """GET /api/products/categories/<slug>/"""
    permission_classes = [AllowAny]

    def get(self, request, slug):
        category = get_object_or_404(Category, slug=slug, is_active=True)
        return Response(CategorySerializer(category).data)


# ══════════════════════════════════════════════════════════════
# PRODUCT VIEWS — Public (listing + detail)
# ══════════════════════════════════════════════════════════════

class ProductListView(generics.ListAPIView):
    """
    GET /api/products/
    GET /api/products/?search=phone
    GET /api/products/?category=electronics
    GET /api/products/?min_price=100&max_price=5000
    GET /api/products/?brand=Apple
    GET /api/products/?in_stock=true
    GET /api/products/?is_featured=true
    GET /api/products/?ordering=-price   (price, -price, avg_rating, -avg_rating, total_sold)
    """
    permission_classes  = [AllowAny]
    serializer_class    = ProductListSerializer
    filter_backends     = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class     = ProductFilter
    search_fields       = ['name', 'description', 'brand', 'category__name']
    ordering_fields     = ['price', 'avg_rating', 'total_sold', 'created_at']
    ordering            = ['-created_at']

    def get_queryset(self):
        return Product.objects.filter(
            status='active'
        ).select_related('category', 'vendor').prefetch_related('images', 'variants', 'stock')


class ProductDetailView(APIView):
    """GET /api/products/<slug>/"""
    permission_classes = [AllowAny]

    def get(self, request, slug):
        product = get_object_or_404(
            Product.objects.select_related('category', 'vendor')
                           .prefetch_related('images', 'variants', 'stock'),
            slug=slug, status='active'
        )
        return Response(ProductDetailSerializer(product).data)


class FeaturedProductsView(APIView):
    """GET /api/products/featured/ — homepage ke liye"""
    permission_classes = [AllowAny]

    def get(self, request):
        products = Product.objects.filter(
            status='active', is_featured=True
        ).select_related('category').prefetch_related('images')[:12]
        return Response(ProductListSerializer(products, many=True).data)


class RelatedProductsView(APIView):
    """GET /api/products/<slug>/related/ — same category ke products"""
    permission_classes = [AllowAny]

    def get(self, request, slug):
        product  = get_object_or_404(Product, slug=slug, status='active')
        related  = Product.objects.filter(
            category=product.category, status='active'
        ).exclude(pk=product.pk).prefetch_related('images')[:8]
        return Response(ProductListSerializer(related, many=True).data)


# ══════════════════════════════════════════════════════════════
# VENDOR VIEWS — Vendor apne products manage kare
# ══════════════════════════════════════════════════════════════

class VendorProductListCreateView(APIView):
    """
    GET  /api/products/my/   — vendor ke apne products
    POST /api/products/my/   — naya product banao
    """
    permission_classes = [IsAuthenticated, IsVendorUser]

    def get(self, request):
        products = Product.objects.filter(
            vendor=request.user
        ).select_related('category').prefetch_related('images')
        return Response(ProductListSerializer(products, many=True).data)

    def post(self, request):
        serializer = ProductWriteSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return Response(ProductDetailSerializer(product).data, status=201)


class VendorProductDetailView(APIView):
    """
    GET    /api/products/my/<id>/   — detail
    PATCH  /api/products/my/<id>/   — update
    DELETE /api/products/my/<id>/   — delete
    """
    permission_classes = [IsAuthenticated, IsVendorUser]

    def _get_product(self, pk, vendor):
        return get_object_or_404(Product, pk=pk, vendor=vendor)

    def get(self, request, pk):
        product = self._get_product(pk, request.user)
        return Response(ProductDetailSerializer(product).data)

    def patch(self, request, pk):
        product = self._get_product(pk, request.user)
        if product.status == 'active':
            return Response({"error": "Active product seedha update nahi ho sakta. Pehle draft mein karo."}, status=400)
        serializer = ProductWriteSerializer(product, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ProductDetailSerializer(product).data)

    def delete(self, request, pk):
        product = self._get_product(pk, request.user)
        product.delete()
        return Response({"message": "Product delete ho gaya."}, status=204)


# ── Product Images ─────────────────────────────────────────────────────────
class ProductImageView(APIView):
    """
    POST   /api/products/my/<id>/images/          — image add karo (URL)
    DELETE /api/products/my/<id>/images/<img_id>/ — image remove karo
    """
    permission_classes = [IsAuthenticated, IsVendorUser]

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk, vendor=request.user)
        data    = request.data.copy()
        # Pehli image automatically primary
        if not product.images.exists():
            data['is_primary'] = True

        serializer = ProductImageSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(product=product)
        return Response(serializer.data, status=201)

    def delete(self, request, pk, img_id):
        product = get_object_or_404(Product, pk=pk, vendor=request.user)
        image   = get_object_or_404(ProductImage, pk=img_id, product=product)
        image.delete()
        return Response({"message": "Image remove ho gayi."}, status=204)


# ── Product Variants ───────────────────────────────────────────────────────
class ProductVariantView(APIView):
    """
    GET  /api/products/my/<id>/variants/         — sabhi variants
    POST /api/products/my/<id>/variants/          — naya variant
    PATCH /api/products/my/<id>/variants/<v_id>/  — update stock/price
    """
    permission_classes = [IsAuthenticated, IsVendorUser]

    def get(self, request, pk):
        product  = get_object_or_404(Product, pk=pk, vendor=request.user)
        variants = product.variants.all()
        return Response(ProductVariantSerializer(variants, many=True).data)

    def post(self, request, pk):
        product    = get_object_or_404(Product, pk=pk, vendor=request.user)
        serializer = ProductVariantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(product=product)
        return Response(serializer.data, status=201)


class ProductVariantDetailView(APIView):
    permission_classes = [IsAuthenticated, IsVendorUser]

    def patch(self, request, pk, v_id):
        product = get_object_or_404(Product, pk=pk, vendor=request.user)
        variant = get_object_or_404(ProductVariant, pk=v_id, product=product)
        serializer = ProductVariantSerializer(variant, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk, v_id):
        product = get_object_or_404(Product, pk=pk, vendor=request.user)
        variant = get_object_or_404(ProductVariant, pk=v_id, product=product)
        variant.delete()
        return Response({"message": "Variant delete ho gaya."}, status=204)


# ── Stock Update ───────────────────────────────────────────────────────────
class StockUpdateView(APIView):
    """PATCH /api/products/my/<id>/stock/ — stock update karo"""
    permission_classes = [IsAuthenticated, IsVendorUser]

    def patch(self, request, pk):
        product = get_object_or_404(Product, pk=pk, vendor=request.user)
        stock, _ = Stock.objects.get_or_create(product=product)
        serializer = StockSerializer(stock, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# ══════════════════════════════════════════════════════════════
# ADMIN VIEWS — Products approve/reject
# ══════════════════════════════════════════════════════════════

class AdminProductListView(APIView):
    """
    GET /api/admin/products/               — sabhi products
    GET /api/admin/products/?status=draft  — filter by status
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        qs = Product.objects.select_related('vendor', 'category').prefetch_related('images')

        status_param = request.query_params.get('status')
        vendor_param = request.query_params.get('vendor')
        search_param = request.query_params.get('search')

        if status_param:
            qs = qs.filter(status=status_param)
        if vendor_param:
            qs = qs.filter(vendor__id=vendor_param)
        if search_param:
            qs = qs.filter(Q(name__icontains=search_param) | Q(brand__icontains=search_param))

        return Response({
            "count": qs.count(),
            "products": ProductListSerializer(qs, many=True).data,
        })


class AdminProductStatusView(APIView):
    """
    PATCH /api/admin/products/<id>/status/
    Body: {"status": "active"} ya {"status": "rejected"}
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def patch(self, request, pk):
        product    = get_object_or_404(Product, pk=pk)
        new_status = request.data.get('status')
        is_featured = request.data.get('is_featured')

        allowed_statuses = ['active', 'inactive', 'rejected', 'draft']
        if new_status and new_status not in allowed_statuses:
            return Response({"error": f"Status '{new_status}' valid nahi hai."}, status=400)

        if new_status:
            product.status = new_status
        if is_featured is not None:
            product.is_featured = is_featured
        product.save()

        return Response({
            "message": f"Product '{product.name}' update ho gaya.",
            "status":  product.status,
            "is_featured": product.is_featured,
        })


class AdminCategoryCreateView(APIView):
    """
    POST  /api/admin/categories/         — naya category
    PATCH /api/admin/categories/<id>/    — update
    DELETE /api/admin/categories/<id>/   — delete
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=201)

    def patch(self, request, pk):
        category   = get_object_or_404(Category, pk=pk)
        serializer = CategorySerializer(category, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        category.is_active = False
        category.save()
        return Response({"message": "Category deactivate ho gayi."}, status=204)
