from django.conf.urls import include, url
from django.contrib.auth.decorators import login_required

from rest_framework import routers

import mozillians.groups.api.v2
import mozillians.users.api.v2
from mozillians.users.views import VouchedAutocomplete


# API v2 URLs
router = routers.DefaultRouter()
router.register(r'users', mozillians.users.api.v2.UserProfileViewSet, base_name='userprofile')
router.register(r'groups', mozillians.groups.api.v2.GroupViewSet, base_name='group')
router.register(r'skills', mozillians.groups.api.v2.SkillViewSet, base_name='skill')

urlpatterns = [
    url(r'^v2/', include((router.urls, None)), name='v2root'),
    # Django-autocomplete-light urls
    url(r'api-v2-autocomplete/$', login_required(VouchedAutocomplete.as_view()),
        name='api-v2-autocomplete'),
]
