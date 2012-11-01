from django.conf.urls.defaults import include, patterns, url

from tastypie.api import Api

import apps.users.api

v1_api = Api(api_name='v1')
v1_api.register(apps.users.api.UserResource())

urlpatterns = patterns('',
    url(r'', include(v1_api.urls)),
)
