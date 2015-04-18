from nose.tools import eq_, ok_

from mozillians.common.decorators import allow_public, allow_unvouched
from mozillians.common.tests import TestCase


class DecoratorsTest(TestCase):

    def test_allow_public_decorator(self):
        def foo():
            pass
        eq_(getattr(foo, '_allow_public', None), None)
        allow_public(foo)
        ok_(foo._allow_public)

    def test_allow_unvouched_decorator(self):
        def foo():
            pass
        eq_(getattr(foo, '_allow_unvouched', None), None)
        allow_unvouched(foo)
        ok_(foo._allow_unvouched)
