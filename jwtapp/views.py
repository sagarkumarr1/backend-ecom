from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import generics, status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import get_object_or_404

from .models import User, OTPVerification, Address
from .serializers import (
    RegisterSerializer,
    MyTokenObtainPairSerializer,
    EmailVerifySerializer,
    ChangePasswordSerializer,
    UserProfileSerializer,
    GoogleLoginSerializer,
    AddressSerializer,
    VendorListSerializer,
    VendorApprovalSerializer,
    AdminUserListSerializer,
    AdminUserDetailSerializer,
)
from .permissions import IsAdminUser, IsVendorUser, IsVendorOrAdmin, IsEmailVerified


# ─── Helper ───────────────────────────────────────────────────────────────
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    refresh['role']              = user.role
    refresh['email']             = user.email
    refresh['full_name']         = user.full_name
    refresh['is_email_verified'] = user.is_email_verified
    return {'refresh': str(refresh), 'access': str(refresh.access_token)}


# ══════════════════════════════════════════════════════════════════════════
# DAY 2 — Auth Views (tumhara existing code, unchanged)
# ══════════════════════════════════════════════════════════════════════════

class RegisterView(generics.CreateAPIView):
    queryset           = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class   = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        otp_obj = OTPVerification.objects.filter(
            user=user, purpose=OTPVerification.PURPOSE_EMAIL_VERIFY, is_used=False
        ).last()
        if otp_obj:
            _send_otp_email(user, otp_obj.otp, purpose='verification')
        return Response({
            "message": "Registration successful! Email pe OTP bheja gaya hai.",
            "email": user.email,
            "role":  user.role,
        }, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response({"error": "refresh token zaroori hai."}, status=400)
            RefreshToken(refresh_token).blacklist()
            return Response({"message": "Logout successful!"}, status=205)
        except Exception:
            return Response({"error": "Invalid token ya already logged out."}, status=400)


class EmailVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EmailVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user    = serializer.validated_data['user']
        otp_obj = serializer.validated_data['otp_obj']
        otp_obj.is_used = True
        otp_obj.save()
        user.is_email_verified = True
        user.save()
        return Response({"message": "Email verify ho gaya!", **get_tokens_for_user(user)})


class ResendVerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "User nahi mila."}, status=404)
        if user.is_email_verified:
            return Response({"message": "Email pehle se verify hai."})
        otp_obj = OTPVerification.create_otp(user, OTPVerification.PURPOSE_EMAIL_VERIFY)
        _send_otp_email(user, otp_obj.otp, purpose='verification')
        return Response({"message": "OTP dobara bhej diya gaya."})


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
            otp_obj = OTPVerification.create_otp(user, OTPVerification.PURPOSE_PASSWORD_RESET)
            _send_otp_email(user, otp_obj.otp, purpose='reset')
        except User.DoesNotExist:
            pass
        return Response({"message": "Agar email registered hai toh OTP bhej diya gaya hai."})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email        = request.data.get('email')
        otp          = request.data.get('otp')
        new_password = request.data.get('new_password')
        if not all([email, otp, new_password]):
            return Response({"error": "email, otp aur new_password teeno zaroori hain."}, status=400)
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "User nahi mila."}, status=404)
        otp_obj = OTPVerification.objects.filter(
            user=user, otp=otp,
            purpose=OTPVerification.PURPOSE_PASSWORD_RESET, is_used=False
        ).last()
        if not otp_obj:
            return Response({"error": "OTP galat hai."}, status=400)
        if otp_obj.is_expired():
            return Response({"error": "OTP expire ho gaya."}, status=400)
        user.set_password(new_password)
        user.save()
        otp_obj.is_used = True
        otp_obj.save()
        return Response({"message": "Password reset ho gaya! Ab login karo."})


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        return Response({"message": "Password change ho gaya!"})


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserProfileSerializer(request.user).data)

    def patch(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            google_data = _verify_google_token(serializer.validated_data['id_token'])
        except ValueError as e:
            return Response({"error": str(e)}, status=400)
        user, created = User.objects.get_or_create(
            email=google_data['email'],
            defaults={
                'full_name': google_data.get('name', ''),
                'google_id': google_data['sub'],
                'avatar':    google_data.get('picture', ''),
                'is_email_verified': True,
                'role': User.CUSTOMER,
            }
        )
        if not created and not user.google_id:
            user.google_id = google_data['sub']
            user.avatar    = google_data.get('picture', '')
            user.is_email_verified = True
            user.save()
        return Response({"message": "Google login successful!", "is_new_user": created, **get_tokens_for_user(user)})


# ══════════════════════════════════════════════════════════════════════════
# DAY 1 — Address Views
# ══════════════════════════════════════════════════════════════════════════

class AddressListCreateView(APIView):
    """
    GET  /api/addresses/   — apne saare addresses
    POST /api/addresses/   — naya address add karo
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        addresses = Address.objects.filter(user=request.user)
        return Response(AddressSerializer(addresses, many=True).data)

    def post(self, request):
        serializer = AddressSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=201)


class AddressDetailView(APIView):
    """
    GET    /api/addresses/<id>/   — ek address
    PATCH  /api/addresses/<id>/   — update
    DELETE /api/addresses/<id>/   — delete
    """
    permission_classes = [IsAuthenticated]

    def _get_address(self, pk, user):
        return get_object_or_404(Address, pk=pk, user=user)

    def get(self, request, pk):
        return Response(AddressSerializer(self._get_address(pk, request.user)).data)

    def patch(self, request, pk):
        address = self._get_address(pk, request.user)
        serializer = AddressSerializer(address, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        self._get_address(pk, request.user).delete()
        return Response({"message": "Address delete ho gaya."}, status=204)


class SetDefaultAddressView(APIView):
    """POST /api/addresses/<id>/set-default/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        address = get_object_or_404(Address, pk=pk, user=request.user)
        address.is_default = True
        address.save()
        return Response({"message": f"'{address.city}' address default set ho gaya."})


# ══════════════════════════════════════════════════════════════════════════
# DAY 3 — User Profile & Permissions (extended)
# ══════════════════════════════════════════════════════════════════════════

class DeactivateAccountView(APIView):
    """
    POST /api/account/deactivate/
    User apna account band kar sakta hai.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        password = request.data.get('password')
        if not password or not request.user.check_password(password):
            return Response({"error": "Password galat hai."}, status=400)
        request.user.is_active = False
        request.user.save()
        return Response({"message": "Account deactivate ho gaya."})


# ══════════════════════════════════════════════════════════════════════════
# DAY 3 — Admin Panel Views
# ══════════════════════════════════════════════════════════════════════════

class AdminDashboardView(APIView):
    """GET /api/admin/dashboard/ — overall stats"""
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        return Response({
            "total_users":       User.objects.count(),
            "total_customers":   User.objects.filter(role='customer').count(),
            "total_vendors":     User.objects.filter(role='vendor').count(),
            "pending_vendors":   User.objects.filter(role='vendor', is_vendor_approved=False).count(),
            "verified_users":    User.objects.filter(is_email_verified=True).count(),
            "inactive_users":    User.objects.filter(is_active=False).count(),
        })


class AdminUserListView(APIView):
    """
    GET /api/admin/users/               — sabhi users
    GET /api/admin/users/?role=customer — filter by role
    GET /api/admin/users/?search=sagar  — search by name/email
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        qs = User.objects.all()

        role   = request.query_params.get('role')
        search = request.query_params.get('search')
        active = request.query_params.get('is_active')

        if role:
            qs = qs.filter(role=role)
        if search:
            qs = qs.filter(
                models.Q(email__icontains=search) |
                models.Q(full_name__icontains=search)
            )
        if active is not None:
            qs = qs.filter(is_active=(active.lower() == 'true'))

        return Response({
            "count": qs.count(),
            "users": AdminUserListSerializer(qs, many=True).data,
        })


class AdminUserDetailView(APIView):
    """
    GET   /api/admin/users/<id>/   — user detail
    PATCH /api/admin/users/<id>/   — update (activate/deactivate)
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        return Response(AdminUserDetailSerializer(user).data)

    def patch(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        serializer = AdminUserDetailSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AdminToggleUserActiveView(APIView):
    """POST /api/admin/users/<id>/toggle-active/ — ban/unban user"""
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user.role == 'admin':
            return Response({"error": "Admin ko ban nahi kar sakte."}, status=400)
        user.is_active = not user.is_active
        user.save()
        action = "activate" if user.is_active else "deactivate"
        return Response({"message": f"User {action} ho gaya.", "is_active": user.is_active})


class VendorListView(APIView):
    """
    GET /api/admin/vendors/                  — sabhi vendors
    GET /api/admin/vendors/?approved=false   — pending vendors
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        qs = User.objects.filter(role=User.VENDOR)
        approved_param = request.query_params.get('approved')
        if approved_param == 'false':
            qs = qs.filter(is_vendor_approved=False)
        elif approved_param == 'true':
            qs = qs.filter(is_vendor_approved=True)
        return Response({"count": qs.count(), "vendors": VendorListSerializer(qs, many=True).data})


class VendorApproveView(APIView):
    """
    PATCH /api/admin/vendors/<id>/approve/
    Body: {"is_vendor_approved": true}
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def patch(self, request, pk):
        vendor = get_object_or_404(User, pk=pk, role=User.VENDOR)
        serializer = VendorApprovalSerializer(vendor, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        _send_vendor_status_email(vendor, approved=vendor.is_vendor_approved)
        action = "approve" if vendor.is_vendor_approved else "reject"
        return Response({
            "message": f"Vendor {action} ho gaya.",
            "vendor":  VendorListSerializer(vendor).data,
        })


# ─── Role-based dashboards ────────────────────────────────────────────────
class ProtectedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"message": f"Welcome {request.user.full_name}!", "role": request.user.role})


class VendorDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsVendorUser]

    def get(self, request):
        return Response({
            "message":             f"Vendor dashboard",
            "shop_name":           request.user.shop_name,
            "is_vendor_approved":  request.user.is_vendor_approved,
            "total_addresses":     request.user.addresses.count(),
        })


# ══════════════════════════════════════════════════════════════════════════
# Private Helpers
# ══════════════════════════════════════════════════════════════════════════

def _send_otp_email(user, otp, purpose='verification'):
    if purpose == 'verification':
        subject = "Email Verify karo — OTP"
        body    = (
            f"Hello {user.full_name},\n\n"
            f"Aapka email verification OTP hai:\n\n    {otp}\n\n"
            f"Ye OTP 10 minute mein expire ho jayega.\n\nRegards,\nTeam"
        )
    else:
        subject = "Password Reset — OTP"
        body    = (
            f"Hello {user.full_name},\n\n"
            f"Aapka password reset OTP hai:\n\n    {otp}\n\n"
            f"Ye OTP 10 minute mein expire ho jayega.\n"
            f"Agar aapne request nahi ki toh ignore karo.\n\nRegards,\nTeam"
        )
    try:
        send_mail(subject, body, settings.EMAIL_HOST_USER, [user.email], fail_silently=False)
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")


def _send_vendor_status_email(vendor, approved):
    subject = "Vendor account approved!" if approved else "Vendor application update"
    body = (
        f"Hello {vendor.full_name},\n\n"
        + (f"Aapka shop '{vendor.shop_name}' approve ho gaya! Ab products list kar sakte hain.\n"
           if approved else
           f"Aapki vendor application approve nahi hui. Admin se contact karo.\n")
        + "\nRegards,\nTeam"
    )
    try:
        send_mail(subject, body, settings.EMAIL_HOST_USER, [vendor.email], fail_silently=False)
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")


def _verify_google_token(id_token_str):
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
    id_info = id_token.verify_oauth2_token(
        id_token_str, google_requests.Request(), settings.GOOGLE_OAUTH2_CLIENT_ID
    )
    if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
        raise ValueError("Invalid Google token issuer.")
    return id_info


# Django models Q import
from django.db import models
