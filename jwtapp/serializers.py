import re
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password
from .models import User, OTPVerification, Address


# ─── 1. JWT Token — extra claims ──────────────────────────────────────────
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role']              = user.role
        token['email']             = user.email
        token['full_name']         = user.full_name
        token['is_email_verified'] = user.is_email_verified
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['role']              = self.user.role
        data['email']             = self.user.email
        data['full_name']         = self.user.full_name
        data['is_email_verified'] = self.user.is_email_verified
        if self.user.is_vendor:
            data['is_vendor_approved'] = self.user.is_vendor_approved
            data['shop_name']          = self.user.shop_name
        return data


# ─── 2. Register ──────────────────────────────────────────────────────────
class RegisterSerializer(serializers.ModelSerializer):
    password         = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    shop_name        = serializers.CharField(required=False, allow_blank=True)
    shop_description = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model  = User
        fields = ('full_name', 'email', 'mobile', 'password', 'role', 'shop_name', 'shop_description')
        extra_kwargs = {'role': {'required': False}}

    def validate_mobile(self, value):
        if value and not re.match(r'^\d{10,15}$', value):
            raise serializers.ValidationError("Mobile 10-15 digits ka hona chahiye.")
        return value

    def validate_role(self, value):
        if value not in [User.CUSTOMER, User.VENDOR]:
            raise serializers.ValidationError("Sirf 'customer' ya 'vendor' allowed hai.")
        return value

    def validate(self, attrs):
        if attrs.get('role') == User.VENDOR and not attrs.get('shop_name'):
            raise serializers.ValidationError({"shop_name": "Vendor ke liye shop_name zaroori hai."})
        return attrs

    def create(self, validated_data):
        role             = validated_data.pop('role', User.CUSTOMER)
        shop_name        = validated_data.pop('shop_name', None)
        shop_description = validated_data.pop('shop_description', None)
        user = User.objects.create_user(role=role, **validated_data)
        if role == User.VENDOR:
            user.shop_name        = shop_name
            user.shop_description = shop_description
            user.save()
        OTPVerification.create_otp(user, OTPVerification.PURPOSE_EMAIL_VERIFY)
        return user


# ─── 3. Email Verify ──────────────────────────────────────────────────────
class EmailVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp   = serializers.CharField(max_length=6)

    def validate(self, attrs):
        try:
            user = User.objects.get(email=attrs['email'])
        except User.DoesNotExist:
            raise serializers.ValidationError("User nahi mila.")

        otp_obj = OTPVerification.objects.filter(
            user=user, otp=attrs['otp'],
            purpose=OTPVerification.PURPOSE_EMAIL_VERIFY, is_used=False
        ).last()

        if not otp_obj:
            raise serializers.ValidationError("OTP galat hai.")
        if otp_obj.is_expired():
            raise serializers.ValidationError("OTP expire ho gaya. Dobara request karo.")

        attrs['user']    = user
        attrs['otp_obj'] = otp_obj
        return attrs


# ─── 4. Change Password ───────────────────────────────────────────────────
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_old_password(self, value):
        if not self.context['request'].user.check_password(value):
            raise serializers.ValidationError("Purana password galat hai.")
        return value


# ─── 5. User Profile ──────────────────────────────────────────────────────
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = (
            'id', 'email', 'mobile', 'full_name', 'role',
            'avatar', 'is_email_verified', 'created_at',
            'shop_name', 'shop_description', 'is_vendor_approved',
        )
        read_only_fields = ('id', 'email', 'role', 'is_email_verified', 'created_at', 'is_vendor_approved')


# ─── 6. Google Login ──────────────────────────────────────────────────────
class GoogleLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField()


# ═══════════════════════════════════════════════════════════════════════════
# Day 1 — Address Serializers
# ═══════════════════════════════════════════════════════════════════════════

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Address
        fields = (
            'id', 'full_name', 'phone', 'address_line1', 'address_line2',
            'city', 'state', 'pincode', 'country', 'address_type',
            'is_default', 'created_at',
        )
        read_only_fields = ('id', 'created_at')

    def validate_phone(self, value):
        if not re.match(r'^\d{10,15}$', value):
            raise serializers.ValidationError("Phone 10-15 digits ka hona chahiye.")
        return value

    def validate_pincode(self, value):
        if not re.match(r'^\d{6}$', value):
            raise serializers.ValidationError("Pincode 6 digits ka hona chahiye.")
        return value

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


# ═══════════════════════════════════════════════════════════════════════════
# Day 3 — Vendor Management Serializers (Admin use karega)
# ═══════════════════════════════════════════════════════════════════════════

class VendorListSerializer(serializers.ModelSerializer):
    total_addresses = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = (
            'id', 'email', 'full_name', 'mobile',
            'shop_name', 'shop_description',
            'is_vendor_approved', 'is_email_verified',
            'total_addresses', 'created_at',
        )

    def get_total_addresses(self, obj):
        return obj.addresses.count()


class VendorApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ('id', 'email', 'full_name', 'shop_name', 'is_vendor_approved')
        read_only_fields = ('id', 'email', 'full_name', 'shop_name')


# ═══════════════════════════════════════════════════════════════════════════
# Day 3 — Admin User Management Serializers
# ═══════════════════════════════════════════════════════════════════════════

class AdminUserListSerializer(serializers.ModelSerializer):
    """Admin sabhi users dekh sakta hai."""
    class Meta:
        model  = User
        fields = (
            'id', 'email', 'full_name', 'mobile', 'role',
            'is_active', 'is_email_verified', 'created_at',
        )


class AdminUserDetailSerializer(serializers.ModelSerializer):
    """Admin user ko activate/deactivate kar sakta hai."""
    class Meta:
        model  = User
        fields = (
            'id', 'email', 'full_name', 'mobile', 'role',
            'is_active', 'is_email_verified', 'avatar',
            'shop_name', 'shop_description', 'is_vendor_approved',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'email', 'role', 'created_at', 'updated_at')
