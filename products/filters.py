import django_filters
from django.db.models import Q
from .models import Product, Category


class ProductFilter(django_filters.FilterSet):
    """
    GET /api/products/?category=electronics
    GET /api/products/?min_price=100&max_price=5000
    GET /api/products/?brand=Nike
    GET /api/products/?in_stock=true
    GET /api/products/?is_featured=true
    GET /api/products/?ordering=-price
    """

    # Price range
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')

    # Category — slug se filter
    category  = django_filters.CharFilter(field_name='category__slug', lookup_expr='iexact')

    # Brand
    brand     = django_filters.CharFilter(lookup_expr='icontains')

    # Featured only
    is_featured = django_filters.BooleanFilter()

    # In stock only
    in_stock = django_filters.CharFilter(method='filter_in_stock')

    # Rating
    min_rating = django_filters.NumberFilter(field_name='avg_rating', lookup_expr='gte')

    class Meta:
        model  = Product
        fields = ['category', 'brand', 'min_price', 'max_price', 'is_featured', 'in_stock', 'min_rating']

    def filter_in_stock(self, queryset, name, value):
        if value and value.lower() == 'true':
            # Variants wale products
            with_variants = queryset.filter(variants__stock__gt=0)
            # Stock model wale products
            without_variants = queryset.filter(stock__quantity__gt=0, variants__isnull=True)
            return (with_variants | without_variants).distinct()
        return queryset
