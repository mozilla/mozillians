from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required

from mozillians.mozspaces.views import CoordinatorAutocomplete


urlpatterns = patterns(
    '',
    # Admin urls for django-autocomplete-light.
    url('coordinator-autocomplete/$', login_required(CoordinatorAutocomplete.as_view()),
        name='coordinator-autocomplete'),
)
