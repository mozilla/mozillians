from django.core.exceptions import ImproperlyConfigured
from django.db.models.signals import pre_save
from django.dispatch import receiver

from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in

import commonware.log

from larper import UserSession

log = commonware.log.getLogger('m.browserid')


@receiver(user_logged_in)
def handle_login(sender, **kwargs):
    request = kwargs['request']
    if 'unique_id' in request.session:
        log.info('Setting unique_id=%s from session on user' %
                 request.session['unique_id'])
        request.user.unique_id = request.session['unique_id']


@receiver(pre_save, sender=User)
def handle_pre_save(sender, instance, **kwargs):
    instance.email = instance.username


class LarperMiddleware(object):
    """
    Responsible for populating the request.user object
    with the following attributes:
    * unique_id

    This complements the assertion management from larper.get_assertion.
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
        else:
            log.debug('User is not authenticated!')

    def process_response(self, request, response):
        UserSession.disconnect(request)
        return response


def _populate(request):
    user = request.user
    session = request.session

    if 'unique_id' in session:
        log.info('Setting unique_id=%s from session on user' %
                 session['unique_id'])
        user.unique_id = session['unique_id']
    elif hasattr(user, 'ldap_user'):
        unique_id = user.ldap_user.attrs['uniqueIdentifier'][0]
        user.unique_id = session['unique_id'] = unique_id
