from django.test.utils import override_settings

from nose.tools import eq_
from mock import patch

from mozillians.common.helpers import gravatar
from mozillians.common.tests import TestCase


class HelperTests(TestCase):
    @override_settings(SITE_URL='http://foobar')
    @patch('mozillians.common.helpers.settings.DEFAULT_AVATAR_URL', '/foo.jpg')
    def test_gravatar(self):
        avatar_url = gravatar('fo', size=80, rating='bar')
        eq_(avatar_url, ('https://secure.gravatar.com/avatar/eed8070249'
                         '39b808083f0031a56e9872?s=80&r=bar&d=http%3A%2F%'
                         '2Ffoobar%2Fmedia%2Fimg%2Funknown.png'))
