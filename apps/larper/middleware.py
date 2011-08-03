from django.core.exceptions import ImproperlyConfigured
from django.contrib.auth.signals import user_logged_in

import larper
from larper import UserSession
from users import forms


def handle_login(sender, **kwargs):
    request = kwargs['request']
    form = forms.AuthenticationForm(request.POST)
    if form.is_valid():
        larper.store_password(request, form.cleaned_data['password'])

user_logged_in.connect(handle_login)


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
            msg = "django.contrib.auth.middleware.AuthenticationMiddleware "
            "is missing from your settings.py"
            raise ImproperlyConfigured(msg)

        user = request.user

        if not hasattr(request, 'session'):
            msg = "django.contrib.sessions.middleware.SessionMiddleware "
            "is missing from your settings.py"
            raise ImproperlyConfigured(msg)

        session = request.session

        if '/en-US/media' not in request.path and\
           request.user.is_authenticated():
            _populate(user, session)

    def process_response(self, request, response):
        UserSession.disconnect(request)
        return response


def _populate(user, session):
    if 'unique_id' in session:
        user.unique_id = session['unique_id']
    else:
        unique_id = user.ldap_user.attrs['uniqueIdentifier'][0]
        user.unique_id = session['unique_id'] = unique_id
