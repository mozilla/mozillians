from collections import namedtuple
from operator import itemgetter
from urllib2 import unquote
from urlparse import urljoin

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db.models import Count, Q

from funfactory import utils
from tastypie import fields
from tastypie import http
from tastypie.bundle import Bundle
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.resources import ModelResource, Resource
from tastypie.serializers import Serializer

from mozillians.api.authenticators import AppAuthentication
from mozillians.api.authorisers import MozillaOfficialAuthorization
from mozillians.api.paginator import Paginator
from mozillians.api.resources import (AdvancedSortingResourceMixIn,
                                      ClientCacheResourceMixIn)
from mozillians.users.models import COUNTRIES, UserProfile


Country = namedtuple('Country', ['country', 'country_name', 'population'])
City = namedtuple('City', ['city', 'country', 'country_name', 'population'])


class CustomQuerySet(object):
    """A custom queryset class.

    Supports database count() on len(), order_by, filter, array
    slicing.

    """

    def __init__(self, queryset):
        self._query = queryset

    def __len__(self):
        return self._query.count()

    def order_by(self, *args):
        return self._query.order_by(*args)

    def filter(self, *args, **kwargs):
        return self._query.filter(*args, **kwargs)

    def __getitem__(self, key):
        if isinstance(key, slice):
            return self._query[key.start:key.stop]
        return self._query[key]


class FakeQuerySet(object):
    """
    Wrap an iterable and make it work like a pretty dumb queryset.
    """
    def __init__(self, iterable):
        # We won't be able to get the data out of this without evaluating
        # the iterable (to sort or index it), so we might as well evaluate
        # it once now.
        self.values = list(iterable)

    def order_by(self, *args):
        return sorted(self.values, key=itemgetter(*args))

    def __getitem__(self, key):
        if isinstance(key, slice):
            return self.values[key.start:key.stop]
        return self.values[key]


class LocationCustomResource(AdvancedSortingResourceMixIn,
                             ClientCacheResourceMixIn, Resource):

    class Meta:
        authentication = AppAuthentication()
        authorization = MozillaOfficialAuthorization()
        list_allowed_methods = ['get']
        serializer = Serializer(formats=['json', 'jsonp'])
        paginator_class = Paginator
        include_resource_uri = False
        detail_allowed_methods = []
        cache_control = {'max-age': 0}

    def get_object_list(self):
        queryset = self.Meta.queryset
        return CustomQuerySet(queryset)

    def obj_get_list(self, request=None, **kwargs):
        obj_list = self.get_object_list()
        filters = self.build_filters(getattr(request, 'GET', None))
        if filters:
            obj_list = self.apply_filters(obj_list, filters)
        return obj_list

    def apply_filters(self, obj_list, applicable_filters):
        mega_filter = Q()
        for db_filter in applicable_filters.values():
            mega_filter &= db_filter
        return obj_list.filter(mega_filter)


def collapse_locations(obj_list, keyname):
    """
    Given a CustomQuerySet object, filter/aggregate it down
    so we just have one item per country or city.

    keyname is 'country' or 'city'.

    Also drop the 'privacy_country' or 'privacy_city' field.

    On input, we might have:

       country   privacy_country  population
         Gr             1            27
         Gr             2            16
         Us             1            13
         Us             2            12

    and we want to end up with

       country   population
         Gr          43
         Us          25

    Returns a CustomQuerySet.
    """

    locations = {}
    delkey = 'privacy_%s' % keyname
    for item in obj_list:
        location = item[keyname]
        if location in locations:
            locations[location]['population'] += item['population']
        else:
            if delkey in item:
                del item[delkey]
            locations[location] = item
    # Turn the dictionary into an iterable of the dict values.
    locations = locations.itervalues()
    # Now we have an iterable of dicts, but an iterable is not a queryset
    queryset = FakeQuerySet(locations)
     # And let's make it a CustomQuerySet again
    queryset = CustomQuerySet(queryset)
    return queryset


class CountryResource(LocationCustomResource):
    country = fields.CharField(attribute='country')
    country_name = fields.CharField(attribute='country_name')
    population = fields.IntegerField(attribute='population')
    url = fields.CharField()

    class Meta(LocationCustomResource.Meta):
        resource_name = 'countries'
        ordering = ['country', 'population']
        queryset = (UserProfile.objects
                    .vouched()
                    .exclude(country='')
                    .values('country', 'privacy_country')
                    .annotate(population=Count('country')))
        default_order = ('country',)
        object_class = Country

    def obj_get_list(self, request=None, **kwargs):
        obj_list = super(CountryResource, self).obj_get_list(request, **kwargs)
        return collapse_locations(obj_list, 'country')

    def build_filters(self, filters=None):
        return None

    def full_dehydrate(self, queryset):
        queryset.obj =  self.Meta.object_class(
            country=queryset.obj['country'],
            population=queryset.obj['population'],
            country_name=COUNTRIES[queryset.obj['country']])
        return super(LocationCustomResource, self).full_dehydrate(queryset)

    def dehydrate_url(self, bundle):
        url = reverse('phonebook:list_country', args=[bundle.obj.country])
        return utils.absolutify(url)


class CityResource(LocationCustomResource):
    city = fields.CharField(attribute='city')
    country = fields.CharField(attribute='country')
    country_name = fields.CharField(attribute='country_name')
    population = fields.IntegerField(attribute='population')
    url = fields.CharField()

    class Meta(LocationCustomResource.Meta):
        resource_name = 'cities'
        ordering = ['city', 'country', 'population']
        queryset = (UserProfile.objects
                    .vouched()
                    .exclude(city='')
                    .exclude(country='')
                    .values('city', 'privacy_city',
                            'country', 'privacy_country')
                    .annotate(population=Count('city')))
        default_order = ('country', 'city')
        object_class = City

    def obj_get_list(self, request=None, **kwargs):
        obj_list = super(CityResource, self).obj_get_list(request, **kwargs)
        return collapse_locations(obj_list, 'city')

    def build_filters(self, filters=None):
        database_filters = {}
        valid_filters = [f for f in filters if f in ['country', 'city']]
        getvalue = lambda x: unquote(filters[x].lower())

        for valid_filter in valid_filters:
            database_filters[valid_filter] = (
                Q(**{'{0}__iexact'.format(valid_filter):
                     getvalue(valid_filter) }))

        return database_filters

    def full_dehydrate(self, queryset):
        queryset.obj =  self.Meta.object_class(
            country=queryset.obj['country'],
            country_name=COUNTRIES[queryset.obj['country']],
            population=queryset.obj['population'],
            city=queryset.obj['city'])
        return super(LocationCustomResource, self).full_dehydrate(queryset)

    def dehydrate_url(self, bundle):
        url = reverse('phonebook:list_city',
                      args=[bundle.obj.country, bundle.obj.city])
        return utils.absolutify(url)


class UserResource(ClientCacheResourceMixIn, ModelResource):
    """User Resource."""
    email = fields.CharField(attribute='user__email', null=True, readonly=True)
    username = fields.CharField(attribute='user__username', null=True, readonly=True)
    vouched_by = fields.IntegerField(attribute='vouched_by__id',
                                     null=True, readonly=True)
    groups = fields.CharField()
    skills = fields.CharField()
    languages = fields.CharField()
    url = fields.CharField()

    class Meta:
        queryset = UserProfile.objects.all()
        authentication = AppAuthentication()
        authorization = MozillaOfficialAuthorization()
        serializer = Serializer(formats=['json', 'jsonp'])
        paginator_class = Paginator
        cache_control = {'max-age': 0}
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get']
        resource_name = 'users'
        restrict_fields = False
        restricted_fields = ['email', 'is_vouched']
        fields = ['id', 'full_name', 'is_vouched', 'website', 'vouched_by',
                  'date_vouched', 'groups', 'skills', 'languages',
                  'bio', 'photo', 'ircname', 'country', 'region', 'city',
                  'date_mozillian', 'timezone', 'email', 'allows_mozilla_sites',
                  'allows_community_sites']

    def build_filters(self, filters=None):
        database_filters = {}
        valid_filters =  [f for f in filters if f in
                          ['email', 'country', 'region', 'city', 'ircname',
                           'username', 'groups', 'languages', 'skills',
                           'is_vouched', 'name']]
        getvalue = lambda x: unquote(filters[x].lower())

        if 'email' in valid_filters:
            database_filters['email'] = Q(
                user__email__iexact=getvalue('email'))

        if 'username' in valid_filters:
            database_filters['username'] = Q(
                user__username__iexact=getvalue('username'))

        if 'name' in valid_filters:
            database_filters['name'] = Q(full_name__iexact=getvalue('name'))

        if 'is_vouched' in valid_filters:
            value = getvalue('is_vouched')
            if value == 'true':
                database_filters['is_vouched'] = Q(is_vouched=True)
            elif value == 'false':
                database_filters['is_vouched'] = Q(is_vouched=False)

        for possible_filter in ['country', 'region', 'city', 'ircname']:
            if possible_filter in valid_filters:
                database_filters[possible_filter] = Q(
                    **{'{0}__iexact'.format(possible_filter):
                       getvalue(possible_filter)})

        for group_filter in ['groups', 'languages', 'skills']:
            if group_filter in valid_filters:
                database_filters[group_filter] = Q(
                    **{'{0}__name__in'.format(group_filter):
                       getvalue(group_filter).split(',')})

        return database_filters

    def dehydrate(self, bundle):
        if (bundle.request.GET.get('restricted', False)
            or not bundle.data['allows_mozilla_sites']):
            data = {}
            for key in self._meta.restricted_fields:
                data[key] = bundle.data[key]
            bundle = Bundle(obj=bundle.obj, data=data, request=bundle.request)
        return bundle

    def dehydrate_groups(self, bundle):
        groups = bundle.obj.groups.values_list('name', flat=True)
        return list(groups)

    def dehydrate_skills(self, bundle):
        skills = bundle.obj.skills.values_list('name', flat=True)
        return list(skills)

    def dehydrate_languages(self, bundle):
        languages = bundle.obj.languages.values_list('name', flat=True)
        return list(languages)

    def dehydrate_photo(self, bundle):
        if bundle.obj.photo:
            return urljoin(settings.SITE_URL, bundle.obj.photo.url)
        return ''

    def dehydrate_url(self, bundle):
        url = reverse('phonebook:profile_view',
                      args=[bundle.obj.user.username])
        return utils.absolutify(url)

    def get_detail(self, request, **kwargs):
        if request.GET.get('restricted', False):
            raise ImmediateHttpResponse(response=http.HttpForbidden())

        return super(UserResource, self).get_detail(request, **kwargs)

    def apply_filters(self, request, applicable_filters):
        if (request.GET.get('restricted', False)
            and 'email' not in applicable_filters
            and len(applicable_filters) != 1):
            raise ImmediateHttpResponse(response=http.HttpForbidden())

        mega_filter = Q()
        for db_filter in applicable_filters.values():
            mega_filter &= db_filter

        if request.GET.get('restricted', False):
            mega_filter &= Q(allows_community_sites=True)

        return UserProfile.objects.complete().filter(mega_filter).distinct().order_by('id')
