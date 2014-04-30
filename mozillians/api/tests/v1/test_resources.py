from mock import MagicMock, patch
from nose.tools import eq_

from mozillians.api.v1.resources import GraphiteMixIn
from mozillians.common.tests import TestCase


class GraphiteMixInTests(TestCase):
    @patch('mozillians.api.v1.resources.statsd.incr')
    def test_statsd_call(self, incr_mock):
        real_wrapper = MagicMock()
        view = MagicMock()

        class Bar(object):
            def wrap_view(self, view):
                return real_wrapper

        class Foo(GraphiteMixIn, Bar):
            def __init__(self):
                self.foo = view
                self.foo.im_class.__name__ = 'foo'
                self.foo.im_func.__name__ = 'bar'

        foo = Foo()
        return_value = foo.wrap_view('foo')('request', 1, second=2)

        eq_(return_value, real_wrapper.return_value)
        real_wrapper.assert_called_with('request', 1, second=2)
        incr_mock.assert_called_with('api.resources.foo.bar')
