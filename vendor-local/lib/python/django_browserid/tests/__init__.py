# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from django.utils.functional import wraps

from mock import patch


def fake_create_user(email):
    pass


class mock_browserid(object):
    """
    Mocks django_browserid verification. Can be used as a context manager or
    as a decorator:

    with mock_browserid('a@b.com'):
        django_browserid.verify('random-token')  # = {'status': 'okay',
                                                 #    'email': 'a@b.com',
                                                 #    ...}

    @mock_browserid(None)
    def browserid_test():
        django_browserid.verify('random-token')  # = False
    """
    def __init__(self, email=None, audience=None, unverified_email=None,
                 pass_mock=False):
        self.pass_mock = pass_mock
        self.patcher = patch('django_browserid.base._verify_http_request')
        self.return_value = {
            u'audience': audience,
            u'email': email,
            u'issuer': u'login.persona.org:443',
            u'status': u'okay' if email is not None else u'failure',
            u'valid-until': 1311377222765
        }
        if unverified_email is not None:
            self.return_value['unverified-email'] = unverified_email
            del self.return_value['email']

    def __enter__(self):
        mock = self.patcher.start()
        mock.return_value = self.return_value
        return mock

    def __exit__(self, exc_type, exc_value, traceback):
        self.patcher.stop()

    def __call__(self, func):
        @wraps(func)
        def inner(*args, **kwargs):
            with self as mock:
                if self.pass_mock:
                    args += (mock,)
                return func(*args, **kwargs)
        return inner


class patch_settings(object):
    """
    Convenient helper for patching settings. Can be used as both a context
    manager and a decorator.

    TODO: Remove when we drop support for Django 1.3 and use override_settings
    instead.
    """
    def __init__(self, **kwargs):
        # Load settings at runtime to get the lazy settings object, and patch
        # the _wrapped settings to avoid deleting settings accidentally.
        from django.conf import settings
        wrapped = settings._wrapped
        self.patches = [patch.object(wrapped, name, value, create=True) for
                        name, value in kwargs.items()]

    def __enter__(self):
        for patcher in self.patches:
            patcher.start()

    def __exit__(self, exc_type, exc_value, traceback):
        for patcher in self.patches:
            patcher.stop()

    def __call__(self, func):
        @wraps(func)
        def inner(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return inner
