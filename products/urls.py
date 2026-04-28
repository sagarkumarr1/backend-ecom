from django.urls import path
from .views import (
    # Public
    CategoryListView, CategoryTreeView, CategoryDetailView,
    ProductListView, ProductDetailView,
    FeaturedProductsView, RelatedProductsView,

    # Vendor
    VendorProductListCreateView, VendorProductDetailView,
    ProductImageView, ProductVariantView, ProductVariantDetailView,
    StockUpdateView,

    # Admin
    AdminProductListView, AdminProductStatusView, AdminCategoryCreateView,
)
from .search_views import (
    ProductSearchView, SearchSuggestionsView,
    TrendingProductsView, BrandListView,
)

urlpatterns = [

    # ── Day 5 — Search ────────────────────────────────────────────────────
    path('search/',                  ProductSearchView.as_view(),      name='product_search'),
    path('search/suggestions/',      SearchSuggestionsView.as_view(),  name='search_suggestions'),
    path('trending/',                TrendingProductsView.as_view(),   name='trending_products'),
    path('brands/',                  BrandListView.as_view(),          name='brand_list'),

    # ── Public — Categories ───────────────────────────────────────────────
    path('categories/',              CategoryListView.as_view(),       name='category_list'),
    path('categories/tree/',         CategoryTreeView.as_view(),       name='category_tree'),
    path('categories/<slug:slug>/',  CategoryDetailView.as_view(),     name='category_detail'),

    # ── Public — Products ─────────────────────────────────────────────────
    path('',                         ProductListView.as_view(),        name='product_list'),
    path('featured/',                FeaturedProductsView.as_view(),   name='featured_products'),
    path('<slug:slug>/',             ProductDetailView.as_view(),      name='product_detail'),
    path('<slug:slug>/related/',     RelatedProductsView.as_view(),    name='related_products'),

    # ── Vendor — My Products ──────────────────────────────────────────────
    path('my/',                      VendorProductListCreateView.as_view(), name='vendor_products'),
    path('my/<uuid:pk>/',            VendorProductDetailView.as_view(),     name='vendor_product_detail'),
    path('my/<uuid:pk>/images/',     ProductImageView.as_view(),            name='product_images'),
    path('my/<uuid:pk>/images/<uuid:img_id>/', ProductImageView.as_view(), name='product_image_delete'),
    path('my/<uuid:pk>/variants/',   ProductVariantView.as_view(),          name='product_variants'),
    path('my/<uuid:pk>/variants/<uuid:v_id>/', ProductVariantDetailView.as_view(), name='product_variant_detail'),
    path('my/<uuid:pk>/stock/',      StockUpdateView.as_view(),             name='product_stock'),

    # ── Admin ─────────────────────────────────────────────────────────────
    path('admin/products/',                  AdminProductListView.as_view(),    name='admin_product_list'),
    path('admin/products/<uuid:pk>/status/', AdminProductStatusView.as_view(),  name='admin_product_status'),
    path('admin/categories/',                AdminCategoryCreateView.as_view(), name='admin_category_create'),
    path('admin/categories/<uuid:pk>/',      AdminCategoryCreateView.as_view(), name='admin_category_detail'),
]
