import os

from django.test.utils import override_settings

from funfactory.urlresolvers import reverse
from nose.tools import eq_

from apps.common.tests.init import TestCase
from django.utils import simplejson


class MessengerTest(TestCase):
	def test_messenger_add(self):
		"""User adds messenger name from edit profile"""
		data = {'username':'thewiz', 'service':'AIM'}
		jdata = simplejson.dumps(data)
		url = reverse('messenger_add')
		response = self.mozillian_client.post(url, jdata, "text/json",            
                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
		eq_(200, response.status_code)

	def test_messenger_remove(self):
		"""Remove messenger name from the edit profile"""
		#repetative
		data = {'username':'thewiz', 'service':'AIM'}
		jdata = simplejson.dumps(data)
		url = reverse('messenger_add')
		response = self.mozillian_client.post(url, jdata, "text/json",            
                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
		print self.mozillian_client.get(reverse('messenger_add'))
		data = {'messenger_pk':1}
		jdata = simplejson.dumps(data)
		url = reverse('messenger_remove')
		response = self.mozillian_client.post(url, jdata, "text/json",            
                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
		eq_(200, response.status_code)

