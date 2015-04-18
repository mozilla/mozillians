# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import logging

from django.conf import settings
try:
    from django.conf.urls import patterns, url
except ImportError:
    from django.conf.urls.defaults import patterns, url
from django.contrib.auth.views import logout
from django.core.exceptions import ImproperlyConfigured

from django_browserid.util import import_function_from_setting

logger = logging.getLogger(__name__)


try:
    Verify = import_function_from_setting('BROWSERID_VERIFY_CLASS')
except ImproperlyConfigured as e:
    logger.info('Loading BROWSERID_VERIFY_CLASS failed: {0}.\nFalling back to '
                'default.'.format(e))
    from django_browserid.views import Verify


urlpatterns = patterns('',
    url(r'^login/', Verify.as_view(), name='browserid_login'),
    url(r'^logout/', logout,
        {'next_page': getattr(settings, 'LOGOUT_REDIRECT_URL', '/')},
        name='browserid_logout')
)
