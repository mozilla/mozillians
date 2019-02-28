from functools import reduce
from operator import or_

from django.db.models import Q
from django.conf import settings
from django.contrib.auth.models import User
from django.http import JsonResponse

from cities_light.models import City, Country, Region
from dal import autocomplete
from pytz import country_timezones

from mozillians.common.templatetags.helpers import get_object_or_none
from mozillians.groups.models import GroupMembership
from mozillians.phonebook.forms import get_timezones_list
from mozillians.users.models import IdpProfile, UserProfile


class BaseProfileAdminAutocomplete(autocomplete.Select2QuerySetView):
    """Base class for django-autocomplete-light."""

    def get_queryset(self):
        """Base queryset used only in admin.

        Return all the users who have completed their profile registration.
        """
        if not self.request.user.is_staff:
            return UserProfile.objects.none()

        qs = UserProfile.objects.complete()
        self.q_base_filter = (Q(full_name__icontains=self.q)
                              | Q(user__email__icontains=self.q)
                              | Q(user__username__icontains=self.q))

        if self.q:
            qs = qs.filter(self.q_base_filter)
        return qs


class UsersAdminAutocomplete(autocomplete.Select2QuerySetView):
    """Base class for django-autocomplete-light."""

    def get_queryset(self):
        """Base queryset used only in admin.

        Return all the users who have completed their profile registration.
        """
        if not self.request.user.is_staff:
            return User.objects.none()

        qs = User.objects.all()
        self.q_base_filter = (Q(userprofile__full_name__icontains=self.q)
                              | Q(email__icontains=self.q)
                              | Q(username__icontains=self.q))

        if self.q:
            qs = qs.filter(self.q_base_filter)
        return qs


class VoucherAutocomplete(BaseProfileAdminAutocomplete):

    def get_queryset(self):
        """Augment base queryset by returning only users who can vouch."""
        qs = super(VoucherAutocomplete, self).get_queryset().filter(can_vouch=True)

        if self.q:
            qs = qs.filter(self.q_base_filter)
        return qs


class VouchedAutocomplete(BaseProfileAdminAutocomplete):

    def get_queryset(self):
        """Augment base queryset by returning only vouched users."""
        qs = super(VouchedAutocomplete, self).get_queryset().vouched()

        if self.q:
            qs = qs.filter(self.q_base_filter)
        return qs


class CuratorsAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        """Augment base queryset by returning only vouched users."""

        # Allow only vouched users to perform this query.
        if not self.request.user.userprofile.is_vouched:
            return UserProfile.objects.none()

        qs = UserProfile.objects.vouched()

        if self.q:
            qs = qs.filter(Q(full_name__icontains=self.q)
                           | Q(user__email__icontains=self.q)
                           | Q(user__username__icontains=self.q))
        return qs


def get_autocomplete_location_query(qs, q):
    """Return qs if ``istartswith`` filter exists, else fallback to ``icontains``."""
    startswith_qs = qs.filter(name__istartswith=q)
    if startswith_qs.exists():
        return startswith_qs
    return qs.filter(name__icontains=q)


class StaffProfilesAutocomplete(autocomplete.Select2QuerySetView):

    def get_results(self, context):
        """Modify the text in the results of the group invitation form."""

        results = []
        for result in context['object_list']:
            pk = self.get_result_value(result)
            if not pk:
                continue

            profile = UserProfile.objects.get(pk=pk)
            idp = get_object_or_none(IdpProfile, profile=profile, primary=True)
            text = self.get_result_label(result)

            # Append the email used for login in the autocomplete text
            if idp:
                text += ' ({0})'.format(idp.email)

            item = {
                'id': pk,
                'text': text
            }
            results.append(item)
        return results

    def get_queryset(self):
        if not self.request.user.userprofile.is_vouched:
            return UserProfile.objects.none()

        queries = []

        # Query staff profiles
        for domain in settings.AUTO_VOUCH_DOMAINS:
            pks = IdpProfile.objects.filter(
                email__endswith='@' + domain).values_list('profile__pk', flat=True)
            queries.append(Q(pk__in=pks))

        query = reduce(or_, queries)

        qs = UserProfile.objects.filter(query).distinct()
        if self.q:
            qs = qs.filter(Q(full_name__icontains=self.q)
                           | Q(user__email__icontains=self.q)
                           | Q(user__username__icontains=self.q))
        return qs


class AccessGroupInvitationAutocomplete(StaffProfilesAutocomplete):

    def get_queryset(self):
        staff_qs = super(AccessGroupInvitationAutocomplete, self).get_queryset()
        staff_ids = staff_qs.values_list('pk', flat=True)

        # Query NDA memberships
        nda_members_ids = GroupMembership.objects.filter(
            group__name=settings.NDA_GROUP,
            status=GroupMembership.MEMBER
        ).values_list('userprofile__pk', flat=True)

        query = Q(pk__in=staff_ids) | Q(pk__in=nda_members_ids)
        qs = UserProfile.objects.filter(query).distinct()
        if self.q:
            qs = qs.filter(Q(full_name__icontains=self.q)
                           | Q(user__email__icontains=self.q)
                           | Q(user__username__icontains=self.q))
        return qs


class NDAGroupInvitationAutocomplete(StaffProfilesAutocomplete):

    def get_queryset(self):
        staff_qs = super(NDAGroupInvitationAutocomplete, self).get_queryset()
        staff_ids = staff_qs.values_list('pk', flat=True)

        mfa_idps_query = (IdpProfile.objects.filter(primary=True)
                                            .filter(Q(type=IdpProfile.PROVIDER_GITHUB)
                                                    | Q(type=IdpProfile.PROVIDER_FIREFOX_ACCOUNTS)
                                                    | Q(type=IdpProfile.PROVIDER_GOOGLE)
                                                    | Q(type=IdpProfile.PROVIDER_LDAP)))
        mfa_idps_pks = mfa_idps_query.values_list('profile__id', flat=True)
        qs = UserProfile.objects.filter(Q(pk__in=mfa_idps_pks) | Q(pk__in=staff_ids))
        if self.q:
            qs = qs.filter(Q(full_name__icontains=self.q)
                           | Q(user__email__icontains=self.q)
                           | Q(user__username__icontains=self.q))
        return qs


class CountryAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        """Country queryset from cities_light."""

        if not self.request.user.is_authenticated():
            return Country.objects.none()
        qs = Country.objects.all()

        if self.q:
            return get_autocomplete_location_query(qs, self.q)
        return qs


class RegionAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        """Region queryset from cities_light."""

        country_id = self.forwarded.get('country')
        if not self.request.user.is_authenticated():
            return Region.objects.none()

        qs = Region.objects.all()
        if country_id:
            country = Country.objects.get(id=country_id)
            qs = qs.filter(country=country)

        if self.q:
            return get_autocomplete_location_query(qs, self.q)
        return qs


class CityAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        """City queryset from cities_light."""

        region_id = self.forwarded.get('region')
        country_id = self.forwarded.get('country')
        if not self.request.user.is_authenticated():
            return City.objects.none()

        qs = City.objects.all()
        if country_id:
            country = Country.objects.get(id=country_id)
            qs = qs.filter(country=country)

        if region_id:
            region = Region.objects.get(id=region_id)
            qs = qs.filter(region=region, country=region.country)

        if self.q:
            return get_autocomplete_location_query(qs, self.q)
        return qs


class TimeZoneAutocomplete(autocomplete.Select2ListView):

    def get_list(self):
        """Timezone list provided from pytz."""

        if not self.request.user.is_authenticated():
            return []

        return get_timezones_list()

    def get(self, request, *args, **kwargs):
        """Override get method to tune the search."""
        results = self.get_list()

        country_id = self.forwarded.get('country')
        region_id = self.forwarded.get('region')
        city_id = self.forwarded.get('city')
        country_code = None

        # Try to get the timezone from the city, region, country
        # forwarded values
        if city_id:
            city = City.objects.get(id=city_id)
            country_code = city.country.code2
        elif region_id:
            region = Region.objects.get(id=region_id)
            country_code = region.country.code2
        elif country_id:
            country = Country.objects.get(id=country_id)
            country_code = country.code2

        if country_code:
            results = country_timezones(country_code)

        if self.q:
            results = [item for item in results if self.q.lower() in item.lower()]

        return JsonResponse({
            'results': [dict(id=x, text=x) for x in results]
        })
