import logging
import json
import requests
import hashlib

from requests.models import Response
from requests.exceptions import Timeout

from django.contrib.auth.models import User
from django.test.utils import override_settings

from funfactory.urlresolvers import reverse
from mock import patch
from nose.tools import ok_, eq_, nottest
from product_details import product_details
from pyquery import PyQuery as pq

from common import browserid_mock
from common.tests import ESTestCase, user
from groups.models import Group

from ..models import UserProfile, UserBadgesException
import users


Group.objects.get_or_create(name='staff', system=True)
COUNTRIES = product_details.get_regions('en-US')

EMAIL = 'robot1337@domain.com'
SALT = 'hooraycats'
EMAIL_HASH = 'sha512$%s' % hashlib.sha512('%s%s' % (EMAIL, SALT))

CONVERT_DATA = {
    u'status': u'okay', u'userId': 222, u'email': EMAIL
}

GROUP_LIST_DATA = {
    u'userId': 222, u'groups': [
        {u'groupId': 256, u'badges': 9, u'name': u'Nifty badges'},
        {u'groupId': 1804, u'badges': 11, u'name': u'Keen badges'},
        {u'groupId': 999, u'badges': 11, u'name': u'mozillians.org'},
    ]
}

BADGES_DATA = {
    u'userId': 761, u'groupId': 1804, u'badges': [
        {
            u'assertionType': u'hosted',
            u'lastValidated': u'2012-05-30T16:07:40.000Z',
            u'imageUrl': u'http://example.com/51f6d.png',
            u'hostedUrl': u'http://example.com/assertion',
            u'assertion': {
                u'recipient': EMAIL,
                u'badge': {
                    u'name': u'Badge Haxxor',
                    u'image': u'http://example.com/zilla.png',
                    u'description': u'You know how to hack badges',
                    u'version': u'0.0.1',
                    u'criteria': u'http://artzilla.org/#thisisafakebadge',
                    u'issuer': {
                        u'origin': u'http://badges-101.openbadges.org/',
                        u'org': u'Experimental Badge Authority',
                        u'contact': u'hai2u@openbadges.org',
                        u'name': u'Open Badges'
                    },
                },
            }, 
        },

        {
            u'assertionType': u'hosted',
            u'imageUrl': u'https://example.com/9793b6b.png',
            u'hostedUrl': u'https://example.com/064ca40359d',
            u'lastValidated': u'2013-01-16T16:09:16.000Z',
            u'assertion': {
                u'salt': SALT,
                u'recipient': EMAIL_HASH,
                u'badge': {
                    u'name': u'Thimble Projectizer',
                    u'image': u'https://example.com/thimble-project.png',
                    u'description': u'For publishing a project',
                    u'version': u'0.5.0',
                    u'criteria': u'https://example.com/projectizer',
                    u'issuer': {
                        u'origin': u'https://badges.webmaker.org',
                        u'org': u'Webmaker',
                        u'contact': u'brian@mozillafoundation.org',
                        u'name': u'Mozilla'
                    },
                },
            },
        },

        {
            u'assertionType': u'hosted',
            u'imageUrl': u'http://example.org/bdbafbee.png',
            u'hostedUrl': u'https://example.org/4588debe5',
            u'lastValidated': u'2013-01-16T17:56:06.000Z',
            u'assertion': {
                u'salt': SALT,
                u'recipient': EMAIL_HASH,
                u'badge': {
                    u'name': u'Hyperlinker',
                    u'image': u'https://example.com/linker.png',
                    u'description': u'A mini skill badge',
                    u'version': u'0.5.0',
                    u'criteria': u'https://example.com/linker',
                    u'issuer': {
                        u'origin': u'https://badges.webmaker.org',
                        u'org': u'Webmaker', 
                        u'contact': u'brian@mozillafoundation.org',
                        u'name': u'Mozilla'
                    },
                },
            },
        },
    ]
}


class OpenbadgeTests(ESTestCase):

    def setUp(self):
        info = dict(full_name='Akaaaaaaash Desaaaaaaai', optin=True)
        self.client.logout()

        u = User.objects.create(username='robot1337', email=EMAIL)
        p = u.get_profile()

        p.full_name = info['full_name']
        u.save()
        p.save()

        self.u = u
        self.p = p

    def tearDown(self):
        self.u.delete()
        self.p.delete()

    @patch('requests.post')
    @patch('requests.get')
    def test_good_fetch(self, mock_requests_get, mock_requests_post):
        """Badges fetched, if everything goes well with Displayer API"""
        # Trap the email-to-uid conversion POST request
        def mock_post(url, **kwargs):
            ok_('displayer/convert/email' in url,
                'POST request should lead to email conversion API')
            ok_('data' in kwargs)
            ok_('email' in kwargs['data'])
            eq_(kwargs['data']['email'], EMAIL)
            resp = Response()
            resp.status_code = 200
            resp._content = json.dumps(CONVERT_DATA)
            return resp

        mock_requests_post.side_effect = mock_post

        # Trap the group list and badges GET requests
        def mock_get(url, **kwargs):
            resp = Response()
            resp.status_code = 200
            if 'groups.json' in url:
                resp._content = json.dumps(GROUP_LIST_DATA)
            elif '222/group/999.json' in url:
                resp._content = json.dumps(BADGES_DATA)
            else:
                ok_(False, 'Unexpected HTTP request')
            return resp

        mock_requests_get.side_effect = mock_get

        # Fetch the badges for the profile, which should kick off the above
        badges = self.p.badges

        # Results should match the sample data
        num_badges = len(BADGES_DATA['badges'])
        eq_(len(badges), num_badges)
        for idx in range(0, num_badges):
            badge = badges[idx]

            # Make sure both raw and attribute access to imageUrl works.
            image_url = BADGES_DATA['badges'][idx]['imageUrl']
            eq_(badge.raw['imageUrl'], image_url)
            eq_(badge.imageUrl, image_url)

            # Check email or hash for recipient
            recipient = badge.recipient
            if badge.salt:
                eq_(recipient, EMAIL_HASH)
            else:
                eq_(recipient, EMAIL)

            # Check some more important attributes
            for f in ('name', 'image', 'description'):
                eq_(getattr(badge, f),
                    BADGES_DATA['badges'][idx]['assertion']['badge'][f])

    @patch('requests.post')
    @patch('requests.get')
    def test_userid_convert_timeout_failure(self, mock_requests_get,
                                            mock_requests_post):
        def mock_post(url, **kwargs):
            raise Timeout('Request timed out.')
        mock_requests_post.side_effect = mock_post
        def mock_get(url, **kwargs):
            ok_(False, 'No GET request should be issued')
        mock_requests_get.side_effect = mock_get
        with self.assertRaises(requests.exceptions.RequestException):
            badges = self.p.fetch_raw_badges()

    @patch('requests.post')
    @patch('requests.get')
    def test_userid_convert_status_failure(self, mock_requests_get,
                                           mock_requests_post):
        def mock_post(url, **kwargs):
            resp = Response()
            resp.status_code = 503
            resp._content = ''
            return resp
        mock_requests_post.side_effect = mock_post
        def mock_get(url, **kwargs):
            ok_(False, 'No GET request should be issued')
        mock_requests_get.side_effect = mock_get
        with self.assertRaises(users.models.UserBadgesException):
            badges = self.p.fetch_raw_badges()
