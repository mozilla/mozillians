import os

from django.conf import settings

from nose.tools import ok_

from mozillians.common.tests import TestCase
from mozillians.humans.cron import generate_humanstxt


class TestCron(TestCase):
    def test_generate(self):
        os.remove(settings.HUMANSTXT_FILE)
        generate_humanstxt()
        ok_(os.path.exists(settings.HUMANSTXT_FILE))
