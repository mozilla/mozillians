from django.conf.urls import include, patterns, url
from django.views.generic import RedirectView

from rest_framework import routers
from tastypie.api import Api

import mozillians.groups.api.v1
import mozillians.users.api.v1
import mozillians.users.api.v2


v1_api = Api(api_name='v1')
v1_api.register(mozillians.users.api.v1.UserResource())
v1_api.register(mozillians.groups.api.v1.GroupResource())
v1_api.register(mozillians.groups.api.v1.SkillResource())

router = routers.DefaultRouter()
router.register(r'user', mozillians.users.api.v2.UserProfileViewSet)

urlpatterns = patterns(
    '',
    url(r'', include(v1_api.urls)),
    url(r'^$', RedirectView.as_view(url='/api/v2/', permanent=False), name='apiroot'),
    url(r'^v2/', include(router.urls)),
)
