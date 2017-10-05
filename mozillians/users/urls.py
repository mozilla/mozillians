from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from cities_light.models import Country
from mozillians.users import views as user_views


app_name = 'users'
urlpatterns = [
    # Admin urls for django-autocomplete-light.
    url('users-autocomplete/$', login_required(user_views.UsersAdminAutocomplete.as_view()),
        name='users-autocomplete'),
    url('vouchee-autocomplete/$', login_required(
        user_views.BaseProfileAdminAutocomplete.as_view()),
        name='vouchee-autocomplete'),
    url('voucher-autocomplete/$', login_required(user_views.VoucherAutocomplete.as_view()),
        name='voucher-autocomplete'),
    url('vouched-autocomplete/$', login_required(user_views.VouchedAutocomplete.as_view()),
        name='vouched-autocomplete'),
    url('country-autocomplete/$', login_required(
        user_views.CountryAutocomplete.as_view(model=Country)),
        name='country-autocomplete'),
    url('region-autocomplete/$', login_required(user_views.RegionAutocomplete.as_view()),
        name='region-autocomplete'),
    url('city-autocomplete/$', login_required(user_views.CityAutocomplete.as_view()),
        name='city-autocomplete'),
    url('timezone-autocomplete/$', login_required(user_views.TimeZoneAutocomplete.as_view()),
        name='timezone-autocomplete'),
    url('staff-autocomplete/$', login_required(user_views.StaffProfilesAutocomplete.as_view()),
        name='staff-autocomplete'),
    url('access-group-invitation-autocomplete/$',
        login_required(user_views.AccessGroupInvitationAutocomplete.as_view()),
        name='access-group-invitation-autocomplete'),
    url('nda-group-invitation-autocomplete/$',
        login_required(user_views.NDAGroupInvitationAutocomplete.as_view()),
        name='nda-group-invitation-autocomplete'),
]
