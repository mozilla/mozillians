from urllib2 import unquote
from urlparse import urljoin

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db.models import Q

from funfactory import utils
from tastypie import fields, http
from tastypie.authorization import ReadOnlyAuthorization
from tastypie.bundle import Bundle
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.resources import ModelResource
from tastypie.serializers import Serializer

from mozillians.api.authenticators import AppAuthentication
from mozillians.api.paginator import Paginator
from mozillians.api.resources import (ClientCacheResourceMixIn,
                                      GraphiteMixIn)
from mozillians.users.models import UserProfile


class UserResource(ClientCacheResourceMixIn, GraphiteMixIn, ModelResource):
    """User Resource."""
    email = fields.CharField(attribute='user__email', null=True, readonly=True)
    username = fields.CharField(attribute='user__username', null=True, readonly=True)
    vouched_by = fields.IntegerField(attribute='vouched_by__id',
                                     null=True, readonly=True)
    date_vouched = fields.DateTimeField(attribute='date_vouched', null=True, readonly=True)

    groups = fields.CharField()
    skills = fields.CharField()
    languages = fields.CharField()
    url = fields.CharField()
    accounts = fields.CharField()

    class Meta:
        queryset = UserProfile.objects.all()
        authentication = AppAuthentication()
        authorization = ReadOnlyAuthorization()
        serializer = Serializer(formats=['json', 'jsonp'])
        paginator_class = Paginator
        cache_control = {'max-age': 0}
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get']
        resource_name = 'users'
        restrict_fields = False
        restricted_fields = ['email', 'is_vouched']
        fields = ['id', 'full_name', 'is_vouched', 'vouched_by',
                  'date_vouched', 'groups', 'skills',
                  'bio', 'photo', 'ircname', 'country', 'region', 'city',
                  'date_mozillian', 'timezone', 'email', 'allows_mozilla_sites',
                  'allows_community_sites']

    def build_filters(self, filters=None):
        database_filters = {}
        valid_filters = [f for f in filters if f in
                         ['email', 'country', 'region', 'city', 'ircname',
                          'username', 'groups', 'skills',
                          'is_vouched', 'name', 'accounts']]
        getvalue = lambda x: unquote(filters[x].lower())

        if 'accounts' in valid_filters:
            database_filters['accounts'] = Q(
                externalaccount__identifier__icontains=getvalue('accounts'))

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

        for group_filter in ['groups', 'skills']:
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

    def dehydrate_accounts(self, bundle):
        accounts = [{'identifier': a.identifier, 'type': a.type}
                    for a in bundle.obj.externalaccount_set.all()]
        return accounts

    def dehydrate_groups(self, bundle):
        groups = bundle.obj.groups.values_list('name', flat=True)
        return list(groups)

    def dehydrate_skills(self, bundle):
        skills = bundle.obj.skills.values_list('name', flat=True)
        return list(skills)

    def dehydrate_languages(self, bundle):
        languages = bundle.obj.languages.values_list('code', flat=True)
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
