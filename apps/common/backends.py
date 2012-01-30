from django.contrib.auth.models import User

from django_browserid.auth import BrowserIDBackend


class MozilliansBrowserID(BrowserIDBackend):
    """
    Special auth backend to allow registration to work without a current
    assertion. This is dangerous. Don't use authenticated_email unless you've
    just verified somebody.
    """

    def authenticate(self, assertion=None, audience=None, authenticated_email=None):
        if authenticated_email:
            users = User.objects.filter(email=email)
            if len(users) > 1:
                log.warn('%d users with email address %s.' % (len(users), email))
                return None
            if len(users) == 1:
                return users[0]

        return super(MozilliansBrowserID, self).authenticate(
                                        assertion=assertion, audience=audience)


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
