import base64
import hashlib
import re
from urlparse import parse_qs, urlparse

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.db import IntegrityError
from django.db.models import Q

from django_browserid.auth import BrowserIDBackend
from django_browserid.base import RemoteVerifier, get_audience
from django_browserid.http import JSONResponse
from django_browserid.views import Verify
from tower import ugettext as _

from mozillians.users.models import ExternalAccount, UserProfile


def calculate_username(email):
    """Calculate username from email address."""

    email = email.split('@')[0]
    username = re.sub(r'[^\w.@+-]', '-', email)
    username = username[:settings.USERNAME_MAX_LENGTH]
    suggested_username = username
    count = 0

    while User.objects.filter(username=suggested_username).exists():
        count += 1
        suggested_username = '%s%d' % (username, count)

        if len(suggested_username) > settings.USERNAME_MAX_LENGTH:
            # We failed to calculate a name for you, default to a
            # email digest.
            return base64.urlsafe_b64encode(
                hashlib.sha1(email).digest()).rstrip('=')

    return suggested_username


class BrowserIDVerify(Verify):
    @property
    def failure_url(self):
        if self.add_email:
            return reverse('phonebook:profile_edit')
        return super(BrowserIDVerify, self).failure_url

    @property
    def success_url(self):
        if self.add_email:
            return reverse('phonebook:profile_edit')
        return super(BrowserIDVerify, self).success_url

    def login_success(self):
        if self.add_email:
            return JSONResponse({
                'redirect': self.success_url
            })
        return super(BrowserIDVerify, self).login_success()

    def login_failure(self):
        if self.add_email:
            return JSONResponse({
                'redirect': self.failure_url
            })
        return super(BrowserIDVerify, self).login_failure()

    def post(self, *args, **kwargs):
        self.add_email = False
        if not self.request.user.is_authenticated():
            return super(BrowserIDVerify, self).post(*args, **kwargs)

        self.add_email = True

        assertion = self.request.POST.get('assertion')
        if not assertion:
            return self.login_failure()

        verifier = RemoteVerifier()
        audience = get_audience(self.request)
        result = verifier.verify(assertion, audience)

        if not result:
            messages.error(self.request, _('Authentication failed.'))
            return self.login_failure()

        email = result.email

        kwargs = {
            'type': ExternalAccount.TYPE_EMAIL,
            'user': self.request.user.userprofile,
            'identifier': email
        }

        email_exists = User.objects.filter(email=email).exists()
        alternate_email_exists = ExternalAccount.objects.filter(**kwargs).exists()

        if email_exists or alternate_email_exists:
            error_msg = "Email '{0}' already exists in the database.".format(email)
            messages.error(self.request, _(error_msg))
            return self.login_failure()

        ExternalAccount.objects.create(**kwargs)
        return self.login_success()


class MozilliansAuthBackend(BrowserIDBackend):
    def create_user(self, email):
        username = calculate_username(email)
        try:
            user = self.User.objects.create_user(username, email)
        except IntegrityError as err:
            try:
                return self.User.objects.get(email=email)
            except self.User.DoesNotExist:
                raise err

        if self.referral_source:
            user.userprofile.referral_source = self.referral_source
            user.userprofile.save()
        return user

    def authenticate(self, *args, **kwargs):
        self.referral_source = None
        http_referer = kwargs['request'].META.get('HTTP_REFERER', '')
        url_params = parse_qs(urlparse(http_referer).query)
        source = url_params.get('source')
        if source:
            source = source[0].lower()
            for csource, _ignore in UserProfile.REFERRAL_SOURCE_CHOICES:
                if source == csource:
                    self.referral_source = source
                    break
        return super(MozilliansAuthBackend, self).authenticate(*args, **kwargs)

    def filter_users_by_email(self, email):
        account_type = ExternalAccount.TYPE_EMAIL
        alternate_emails = ExternalAccount.objects.filter(type=account_type, identifier=email)
        primary_email_qs = Q(email=email)
        alternate_email_qs = Q(userprofile__externalaccount=alternate_emails)
        return self.User.objects.filter(primary_email_qs | alternate_email_qs).distinct()
