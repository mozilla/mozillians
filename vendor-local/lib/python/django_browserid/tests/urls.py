# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from django.conf.urls.defaults import include, patterns, url
from django.http import HttpResponse


urlpatterns = patterns('',
    (r'^browserid/', include('django_browserid.urls')),
    url(r'^epic-fail/', lambda r: HttpResponse('this is a stub'),
        name='epic_fail')
)
