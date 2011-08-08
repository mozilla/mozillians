from nose.tools import eq_

from django.conf import settings

from commons import helpers


def test_absolutify():
    protocol = settings.PROTOCOL
    hostname = settings.DOMAIN
    port = settings.PORT
    expected = '%s%s:%s/boo' % (protocol, hostname, port)
    eq_(helpers.absolutify('/boo'), expected)
