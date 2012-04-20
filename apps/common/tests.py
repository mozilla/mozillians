from django import test
from django.conf import settings
from django.contrib.auth.models import User

import elasticutils.tests
import test_utils
from elasticutils import get_es

from phonebook.helpers import VOUCHED


class TestCase(test_utils.TestCase):
    @classmethod
    def setUpClass(cls):
        super(TestCase, cls).setUpClass()
        cls._AUTHENTICATION_BACKENDS = settings.AUTHENTICATION_BACKENDS
        settings.AUTHENTICATION_BACKENDS = ('common.backends.TestBackend',)
        # Create a Mozillian
        cls.mozillian = User.objects.create(
                email='u000001@mozillians.org', username='7f3a67u000001',
                first_name='Amandeep', last_name='McIlrath')
        profile = cls.mozillian.get_profile()
        profile.is_vouched = True
        profile.save()

        # Create a non-vouched account
        cls.pending = User.objects.create(
                email='pending@mozillians.org', username='pending',
                first_name='Amanda', last_name='Younger')

    def setUp(self):
        # TODO: can this be more elegant?
        self.client.get('/')
        self.mozillian_client = test.Client()
        self.mozillian_client.login(email=self.mozillian.email)
        self.pending_client = test.Client()
        self.pending_client.login(email=self.pending.email)
        # Basic privacy options to include with tests that post to edit profile
        self.privacy_dict = dict(
                basic_info_privacy=VOUCHED,
                contact_info_privacy=VOUCHED,
                tags_privacy=VOUCHED)

    @classmethod
    def tearDownClass(cls):
        super(TestCase, cls).tearDownClass()
        settings.AUTHENTICATION_BACKENDS = cls._AUTHENTICATION_BACKENDS
        User.objects.all().delete()


class ESTestCase(TestCase, elasticutils.tests.ESTestCase):
    @classmethod
    def setUpClass(cls):
        """Runs the :class:`TestCase` setup to add some data.

        Also flushes and refreshes the data so it's searchable via computer.
        """
        elasticutils.tests.ESTestCase.setUpClass()
        TestCase.setUpClass()
        get_es().flush(refresh=True)

    @classmethod
    def tearDownClass(cls):
        TestCase.tearDownClass()
        elasticutils.tests.ESTestCase.tearDownClass()
