from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from .models import User


class EmailOrMobileBackend(ModelBackend):
    """
    Email ya Mobile number dono se login allow karta hai.
    Example:
        email: "sagar@example.com" + password
        mobile: "9876543210"     + password
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        try:
            user = User.objects.get(
                Q(email__iexact=username) | Q(mobile=username)
            )
        except User.DoesNotExist:
            # Timing attack se bachne ke liye dummy check
            User().set_password(password)
            return None
        except User.MultipleObjectsReturned:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None
