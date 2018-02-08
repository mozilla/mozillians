from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from mozillians.mozspaces import views


app_name = 'mozspaces'
urlpatterns = [
    # Admin urls for django-autocomplete-light.
    url('coordinator-autocomplete/$', login_required(views.CoordinatorAutocomplete.as_view()),
        name='coordinator-autocomplete'),
]
