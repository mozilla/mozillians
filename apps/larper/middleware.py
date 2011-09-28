from django.core.exceptions import ImproperlyConfigured
from django.db.models.signals import pre_save
from django.dispatch import receiver

from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in

import larper
from larper import UserSession


def handle_login(sender, **kwargs):
    request = kwargs['request']
    larper.store_password(request, request.POST.get('password', ''))

user_logged_in.connect(handle_login)


@receiver(pre_save, sender=User)
def handle_pre_save(sender, instance, **kwargs):
    instance.email = instance.username


class LarperMiddleware(object):
    """
    Responsible for populating the request.user object
    with the following attributes:
    * unique_id

    This complements the dn and password management from larper.dn and
    larper.password
    """
    def process_request(self, request):
        if not hasattr(request, 'user'):
            msg = ('django.contrib.auth.middleware.AuthenticationMiddleware '
                   'is missing from your settings.py')
            raise ImproperlyConfigured(msg)

        if not hasattr(request, 'session'):
            msg = ('django.contrib.sessions.middleware.SessionMiddleware '
                   'is missing from your settings.py')
            raise ImproperlyConfigured(msg)

        if request.user.is_authenticated():
            _populate(request)

    def process_response(self, request, response):
        UserSession.disconnect(request)
        return response


def is_vouched(request):
    user = request.user

    def f():
        if not hasattr(user, 'person'):
            directory = UserSession.connect(request)
            # Stale data okay
            user.person = directory.get_by_unique_id(user.unique_id)
        # Presence of voucher DN is enough, don't validate
        return bool(user.person.voucher_unique_id)
    return f


def _populate(request):
    user = request.user
    session = request.session

    if 'unique_id' in session:
        user.unique_id = session['unique_id']
    else:
        unique_id = user.ldap_user.attrs['uniqueIdentifier'][0]
        user.unique_id = session['unique_id'] = unique_id

    user.is_vouched = is_vouched(request)
