from rest_framework import permissions


class IsAdminUser(permissions.BasePermission):
    """Sirf Admin role wale access kar sakte hain."""
    message = "Access denied. Admin role required."

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'admin'
        )


class IsVendorUser(permissions.BasePermission):
    """Sirf approved Vendor access kar sakta hai."""
    message = "Access denied. Approved Vendor role required."

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'vendor' and
            request.user.is_vendor_approved
        )


class IsVendorOrAdmin(permissions.BasePermission):
    """Vendor ya Admin dono access kar sakte hain."""
    message = "Access denied. Vendor or Admin role required."

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in ['vendor', 'admin']
        )


class IsCustomerUser(permissions.BasePermission):
    """Sirf Customer role wale access kar sakte hain."""
    message = "Access denied. Customer role required."

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'customer'
        )


class IsEmailVerified(permissions.BasePermission):
    """
    Sirf verified email wale users hi sensitive actions kar sakte hain.
    IsAuthenticated ke saath use karo.
    """
    message = "Email verified nahi hai. Pehle email verify karo."

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_email_verified
        )
