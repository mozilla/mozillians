from django.conf import settings
from django.utils.functional import wraps
from mock import patch


class mock_browserid(object):
    """
    TODO: This should be in django-browserid
    Mocks django_browserid verification. Can be used as a context manager or
    as a decorator:

    with mock_browserid('a@b.com'):
    django_browserid.verify('random-token') # = {'status': 'okay',
    # 'email': 'a@b.com'}

    @mock_browserid(None)
    def browserid_test():
    django_browserid.verify('random-token') # = False

    Stolen shamelessly from osmose / affiliates
    """
    def __init__(self, email=None):
        self.settings_patches = (
            patch.object(
                settings, 'AUTHENTICATION_BACKENDS',
                ('django_browserid.auth.BrowserIDBackend',),
            ),
            patch.object(
                settings, 'SITE_URL',
                'http://testserver',
            ),
        )
        self.patcher = patch(
            'django_browserid.auth.BrowserIDBackend._verify_http_request')
        if email is not None:
            self.return_value = {'status': 'okay', 'email': email}
        else:
            self.return_value = {'status': 'failure'}

    def __enter__(self):
        for patch in self.settings_patches:
            patch.start()
        self.patcher.start().return_value = self.return_value

    def __exit__(self, exc_type, exc_value, traceback):
        for patch in self.settings_patches:
            patch.stop()
        self.patcher.stop()

    def __call__(self, func):
        @wraps(func)
        def inner(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return inner
