from django.conf.urls import include, patterns, url

from rest_framework import routers
from tastypie.api import Api

import mozillians.groups.api.v1
import mozillians.groups.api.v2
import mozillians.users.api.v1
import mozillians.users.api.v2


# API v1 URLs
v1_api = Api(api_name='v1')
v1_api.register(mozillians.users.api.v1.UserResource())
v1_api.register(mozillians.groups.api.v1.GroupResource())
v1_api.register(mozillians.groups.api.v1.SkillResource())

# API v2 URLs
router = routers.DefaultRouter()
router.register(r'users', mozillians.users.api.v2.UserProfileViewSet)
router.register(r'groups', mozillians.groups.api.v2.GroupViewSet)
router.register(r'skills', mozillians.groups.api.v2.SkillViewSet)

urlpatterns = patterns(
    '',
    url(r'', include(v1_api.urls)),
    url(r'^v2/', include(router.urls), name='v2root'),
)
