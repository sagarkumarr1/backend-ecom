from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, OTPVerification, Address


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = ('email', 'full_name', 'role', 'is_email_verified', 'is_active', 'created_at')
    list_filter   = ('role', 'is_active', 'is_email_verified', 'is_vendor_approved')
    search_fields = ('email', 'full_name', 'mobile')
    ordering      = ('-created_at',)

    fieldsets = (
        ('Login Info',    {'fields': ('email', 'password')}),
        ('Personal',      {'fields': ('full_name', 'mobile', 'avatar')}),
        ('Role & Status', {'fields': ('role', 'is_email_verified', 'is_active', 'is_staff')}),
        ('Vendor Info',   {'fields': ('shop_name', 'shop_description', 'is_vendor_approved')}),
        ('Social',        {'fields': ('google_id',)}),
        ('Permissions',   {'fields': ('is_superuser', 'groups', 'user_permissions')}),
    )

    add_fieldsets = ((None, {
        'classes': ('wide',),
        'fields':  ('email', 'full_name', 'role', 'password1', 'password2'),
    }),)

    actions = ['approve_vendors', 'disapprove_vendors', 'activate_users', 'deactivate_users']

    def approve_vendors(self, request, queryset):
        queryset.filter(role='vendor').update(is_vendor_approved=True)
        self.message_user(request, "Vendors approved!")
    approve_vendors.short_description = "Selected vendors approve karo"

    def disapprove_vendors(self, request, queryset):
        queryset.filter(role='vendor').update(is_vendor_approved=False)
        self.message_user(request, "Vendors disapproved!")
    disapprove_vendors.short_description = "Selected vendors disapprove karo"

    def activate_users(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, "Users activated!")
    activate_users.short_description = "Selected users activate karo"

    def deactivate_users(self, request, queryset):
        queryset.exclude(role='admin').update(is_active=False)
        self.message_user(request, "Users deactivated!")
    deactivate_users.short_description = "Selected users deactivate karo"


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display  = ('user', 'full_name', 'city', 'state', 'pincode', 'is_default', 'address_type')
    list_filter   = ('address_type', 'is_default', 'state')
    search_fields = ('user__email', 'full_name', 'city', 'pincode')
    raw_id_fields = ('user',)


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display    = ('user', 'purpose', 'is_used', 'created_at', 'expires_at')
    list_filter     = ('purpose', 'is_used')
    search_fields   = ('user__email',)
    readonly_fields = ('created_at',)
