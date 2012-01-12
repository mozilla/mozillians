from django.contrib.auth.models import User


class TestBackend(object):
    supports_inactive_user = True

    """Testing backend that does no real authentication.  Great for gags."""
    def authenticate(self, email=None, username=None, password=None):
        if not email:
            email = username
        try:
            return User.objects.get(email=email)
        except User.DoesNotExist:
            pass

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
