from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    # Auth (Day 2)
    RegisterView, LoginView, LogoutView,
    EmailVerifyView, ResendVerifyOTPView,
    PasswordResetRequestView, PasswordResetConfirmView,
    ChangePasswordView, ProfileView, GoogleLoginView,

    # Address (Day 1)
    AddressListCreateView, AddressDetailView, SetDefaultAddressView,

    # User Account (Day 3)
    DeactivateAccountView,

    # Admin Panel (Day 3)
    AdminDashboardView, AdminUserListView, AdminUserDetailView,
    AdminToggleUserActiveView,
    VendorListView, VendorApproveView,

    # Dashboards
    ProtectedView, VendorDashboardView,
)

urlpatterns = [

    # ── Auth ─────────────────────────────────────────────────────────────
    path('register/',      RegisterView.as_view(),    name='auth_register'),
    path('login/',         LoginView.as_view(),        name='auth_login'),
    path('logout/',        LogoutView.as_view(),       name='auth_logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # ── Email Verification ───────────────────────────────────────────────
    path('email/verify/',     EmailVerifyView.as_view(),     name='email_verify'),
    path('email/resend-otp/', ResendVerifyOTPView.as_view(), name='resend_otp'),

    # ── Password ─────────────────────────────────────────────────────────
    path('password/reset/',         PasswordResetRequestView.as_view(), name='password_reset'),
    path('password/reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password/change/',        ChangePasswordView.as_view(),       name='password_change'),

    # ── Profile ──────────────────────────────────────────────────────────
    path('profile/', ProfileView.as_view(), name='profile'),

    # ── Google OAuth ─────────────────────────────────────────────────────
    path('auth/google/', GoogleLoginView.as_view(), name='google_login'),

    # ── Addresses (Day 1) ────────────────────────────────────────────────
    path('addresses/',                       AddressListCreateView.as_view(), name='address_list'),
    path('addresses/<uuid:pk>/',             AddressDetailView.as_view(),     name='address_detail'),
    path('addresses/<uuid:pk>/set-default/', SetDefaultAddressView.as_view(), name='address_default'),

    # ── Account (Day 3) ──────────────────────────────────────────────────
    path('account/deactivate/', DeactivateAccountView.as_view(), name='account_deactivate'),

    # ── Admin — Dashboard & Users (Day 3) ────────────────────────────────
    path('admin/dashboard/',                        AdminDashboardView.as_view(),       name='admin_dashboard'),
    path('admin/users/',                            AdminUserListView.as_view(),         name='admin_users'),
    path('admin/users/<uuid:pk>/',                  AdminUserDetailView.as_view(),       name='admin_user_detail'),
    path('admin/users/<uuid:pk>/toggle-active/',    AdminToggleUserActiveView.as_view(), name='admin_toggle_active'),

    # ── Admin — Vendor Management (Day 3) ────────────────────────────────
    path('admin/vendors/',                   VendorListView.as_view(),   name='vendor_list'),
    path('admin/vendors/<uuid:pk>/approve/', VendorApproveView.as_view(), name='vendor_approve'),

    # ── Dashboards ───────────────────────────────────────────────────────
    path('protected/',        ProtectedView.as_view(),      name='protected'),
    path('vendor/dashboard/', VendorDashboardView.as_view(), name='vendor_dashboard'),
]
