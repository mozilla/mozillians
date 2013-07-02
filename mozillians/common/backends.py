from django.contrib.auth.models import User

import commonware.log

log = commonware.log.getLogger('b.common')


class TestBackend(object):
    """Testing backend that does no real authentication. Great for
    gags.

    """
    supports_inactive_user = True

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
