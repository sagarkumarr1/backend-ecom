from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth + Users (Day 1-3)
    path('api/', include('jwtapp.urls')),

    # Products (Day 4-5)
    path('api/products/', include('products.urls')),

    # Cart + Wishlist + Coupons (Day 6)
    path('api/cart/', include('cart.urls')),

    # Orders (Day 7)
    path('api/orders/', include('orders.urls')),

    # Payments - Razorpay (Day 8)
    path('api/payments/', include('payments.urls')),

    # Reviews (Day 10)
    path('api/reviews/', include('reviews.urls')),

    # Analytics (Day 11-12)
    path('api/admin/analytics/', include('jwtapp.analytics_urls')),

    # API Docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/',   SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/',  SpectacularRedocView.as_view(url_name='schema'),   name='redoc'),
]
