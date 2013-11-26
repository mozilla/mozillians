from django.template import Context
from django.test.utils import override_settings

from bleach import clean
from jingo import env
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
                         '2Ffoobar%2Fmedia%2Fimg%2Fdefault_avatar.png'))

    @patch('mozillians.common.helpers.markdown_module.markdown', wraps=markdown)
    @patch('mozillians.common.helpers.bleach.clean', wraps=clean)
    def test_markdown(self, clean_mock, markdown_mock):
        returned_text = helpers.markdown('***foo***', allowed_tags=['strong'])
        eq_(returned_text, '<strong>foo</strong>')
        ok_(clean_mock.called)
        ok_(markdown_mock.called)

    @override_settings(DEBUG=True,
                       TEMPLATE_LOADERS=('jingo.Loader',))
    def test_display_context(self):
        # With DEBUG on,  display_context() inserts the values of context vars
        t = env.from_string('START{{ display_context() }}END')
        c = Context({'testkey': 'testvalue'})
        s = t.render(c)
        ok_('START<dl' in s)
        ok_('</dl>END' in s)
        ok_("<dt>testkey</dt><dd>'testvalue'</dd>" in s)

    @override_settings(DEBUG=False,
                       TEMPLATE_LOADERS=('jingo.Loader',))
    def test_display_context_production(self):
        # With DEBUG off, display_context() is empty
        t = env.from_string('START{{ display_context() }}END')
        c = Context({'testkey': 'testvalue'})
        s = t.render(c)
        eq_('STARTEND', s)
