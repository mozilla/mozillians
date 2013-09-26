from django.test.utils import override_settings

from bleach import clean
from markdown import markdown
from mock import patch
from nose.tools import eq_, ok_

from mozillians.common import helpers
from mozillians.common.tests import TestCase


class HelperTests(TestCase):
    @override_settings(SITE_URL='http://foobar')
    @patch('mozillians.common.helpers.settings.DEFAULT_AVATAR_URL', '/foo.jpg')
    def test_gravatar(self):
        avatar_url = helpers.gravatar('fo', size=80, rating='bar')
        eq_(avatar_url, ('https://secure.gravatar.com/avatar/eed8070249'
                         '39b808083f0031a56e9872?s=80&r=bar&d=http%3A%2F%'
                         '2Ffoobar%2Fmedia%2Fimg%2Funknown.png'))

    @patch('mozillians.common.helpers.markdown_module.markdown', wraps=markdown)
    @patch('mozillians.common.helpers.bleach.clean', wraps=clean)
    def test_markdown(self, clean_mock, markdown_mock):
        returned_text = helpers.markdown('***foo***', allowed_tags=['strong'])
        eq_(returned_text, '<strong>foo</strong>')
        ok_(clean_mock.called)
        ok_(markdown_mock.called)
