"""
products/search_views.py
Day 5 — Advanced Search
PostgreSQL full-text search + suggestions + trending
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db.models import Q, F
from django.db.models.functions import Greatest
from .models import Product, Category
from .serializers import ProductListSerializer, CategorySerializer


class ProductSearchView(APIView):
    """
    GET /api/products/search/?q=iphone
    GET /api/products/search/?q=phone&category=electronics&min_price=5000&max_price=50000
    GET /api/products/search/?q=nike&ordering=-avg_rating

    Full-text search — name, description, brand, category name
    """
    permission_classes = [AllowAny]

    def get(self, request):
        query      = request.query_params.get('q', '').strip()
        category   = request.query_params.get('category', '')
        min_price  = request.query_params.get('min_price')
        max_price  = request.query_params.get('max_price')
        brand      = request.query_params.get('brand', '')
        ordering   = request.query_params.get('ordering', '-total_sold')
        in_stock   = request.query_params.get('in_stock', '')
        min_rating = request.query_params.get('min_rating')

        qs = Product.objects.filter(status='active').select_related(
            'category', 'vendor'
        ).prefetch_related('images')

        # ── Full text search ──────────────────────────────────────────────
        if query:
            qs = qs.filter(
                Q(name__icontains=query)        |
                Q(brand__icontains=query)       |
                Q(description__icontains=query) |
                Q(category__name__icontains=query)
            ).distinct()

        # ── Filters ───────────────────────────────────────────────────────
        if category:
            qs = qs.filter(category__slug__iexact=category)
        if brand:
            qs = qs.filter(brand__icontains=brand)
        if min_price:
            qs = qs.filter(price__gte=min_price)
        if max_price:
            qs = qs.filter(price__lte=max_price)
        if min_rating:
            qs = qs.filter(avg_rating__gte=min_rating)
        if in_stock == 'true':
            qs = qs.filter(
                Q(variants__stock__gt=0) | Q(stock__quantity__gt=0)
            ).distinct()

        # ── Ordering ──────────────────────────────────────────────────────
        allowed_orderings = {
            'price': 'price',
            '-price': '-price',
            'avg_rating': 'avg_rating',
            '-avg_rating': '-avg_rating',
            'total_sold': 'total_sold',
            '-total_sold': '-total_sold',
            'newest': '-created_at',
        }
        order_field = allowed_orderings.get(ordering, '-total_sold')
        qs = qs.order_by(order_field)

        # ── Pagination (simple) ───────────────────────────────────────────
        page      = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        start     = (page - 1) * page_size
        end       = start + page_size
        total     = qs.count()

        return Response({
            'query':       query,
            'count':       total,
            'page':        page,
            'total_pages': -(-total // page_size),  # ceiling division
            'results':     ProductListSerializer(qs[start:end], many=True).data,
        })


class SearchSuggestionsView(APIView):
    """
    GET /api/products/search/suggestions/?q=ip
    Autocomplete ke liye — fast lightweight response
    """
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        if len(query) < 2:
            return Response({'suggestions': []})

        # Products
        products = Product.objects.filter(
            status='active', name__icontains=query
        ).values('name', 'slug')[:5]

        # Brands
        brands = Product.objects.filter(
            status='active', brand__icontains=query
        ).values_list('brand', flat=True).distinct()[:3]

        # Categories
        categories = Category.objects.filter(
            is_active=True, name__icontains=query
        ).values('name', 'slug')[:3]

        return Response({
            'suggestions': {
                'products':   list(products),
                'brands':     list(brands),
                'categories': list(categories),
            }
        })


class TrendingProductsView(APIView):
    """
    GET /api/products/trending/
    Most sold + highest rated products
    """
    permission_classes = [AllowAny]

    def get(self, request):
        products = Product.objects.filter(
            status='active'
        ).order_by('-total_sold', '-avg_rating').prefetch_related('images')[:10]
        return Response(ProductListSerializer(products, many=True).data)


class BrandListView(APIView):
    """
    GET /api/products/brands/
    Sabhi unique brands ki list — filter ke liye
    """
    permission_classes = [AllowAny]

    def get(self, request):
        brands = Product.objects.filter(
            status='active'
        ).exclude(brand='').values_list('brand', flat=True).distinct().order_by('brand')
        return Response({'brands': list(brands)})
