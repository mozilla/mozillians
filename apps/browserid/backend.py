import ldap

from django.contrib.auth.models import User

import commonware.log
from statsd import statsd

from larper import UserSession, store_assertion


log = commonware.log.getLogger('m.browserid')


class SaslBrowserIDBackend(object):
    """Authentication backend that is SASL aware.

    Authenticates the user's BrowserID assertion and our audience
    with the LDAP server via the SASL BROWSER-ID authentication
    mechanism.
    """
    supports_object_permissions = False
    supports_anonymous_user = False
    supports_inactive_user = False

    def authenticate(self, request=None, assertion=None):
        """Authentication based on BrowserID assertion.

        ``django.contrib.auth`` backend that is SASL and BrowserID
        savy. Uses session to maintain assertion over multiple
        requests.
        """
        if not (request and assertion):
            return None
        store_assertion(request, assertion)

        directory = UserSession(request)
        registered = False
        try:
            (registered, details) = directory.registered_user()
            if registered:
                request.session['unique_id'] = details
            else:
                request.session['verified_email'] = details
        except ldap.OTHER, o:
            statsd.incr('browserid.stale_assertion_or_ldap_error')
            log.error("LDAP error, clearing session assertion [%s]", o)
            store_assertion(request, None)
        except Exception, e:
            statsd.incr('browserid.unknown_error_checking_registered_user')
            log.error("Unknown error, clearing session assertion [%s]", e)
            store_assertion(request, None)

        if registered:
            person = directory.get_by_unique_id(details)
            defaults = dict(username=person.username,
                            first_name=person.first_name,
                            last_name=person.last_name,
                            email=person.username)
            user, created = User.objects.get_or_create(username=person.username,
                                                       defaults=defaults)
            if created:
                user.set_unusable_password()
                user.save()
            return user
        return None

    def get_user(self, user_id):
        """Django auth callback for loading a user."""
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            log.debug("No user found")
            return None
