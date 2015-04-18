import json

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test.client import Client

from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase


class TestViews(TestCase):
    def test_base(self):
        client = Client()
        response = client.get(reverse('humans:humans'))
        eq_(response.status_code, 302)
        ok_(settings.HUMANSTXT_URL in response._headers['location'][1])


class TestContribute(TestCase):
    def test_base(self):
        client = Client()
        response = client.get(reverse('humans:contribute-view'))
        eq_(response.status_code, 200)
        ok_(json.loads(response.content))
        eq_(response['Content-Type'], 'application/json')
