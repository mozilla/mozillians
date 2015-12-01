from django.db.models import Q
from django.shortcuts import get_object_or_404

import django_filters
from funfactory.urlresolvers import reverse
from rest_framework import viewsets, serializers
from rest_framework.response import Response

from mozillians.common.helpers import absolutify, markdown
from mozillians.users.managers import PUBLIC
from mozillians.users.models import ExternalAccount, GroupMembership, Language, UserProfile


# Serializers

class ExternalAccountSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='get_type_display')
    privacy = serializers.CharField(source='get_privacy_display')

    class Meta:
        model = ExternalAccount
        fields = ('type', 'identifier', 'privacy', 'name')

    def transform_type(self, obj, value):
        return value.lower()


class WebsiteSerializer(serializers.ModelSerializer):
    website = serializers.CharField(source='identifier')
    privacy = serializers.CharField(source='get_privacy_display')

    class Meta:
        model = ExternalAccount
        fields = ('website', 'privacy')


class LanguageSerializer(serializers.ModelSerializer):
    english = serializers.CharField(source='get_english')
    native = serializers.CharField(source='get_native')

    class Meta:
        model = Language
        fields = ('code', 'english', 'native')


class AlternateEmailSerializer(serializers.ModelSerializer):
    email = serializers.CharField(source='identifier')
    privacy = serializers.CharField(source='get_privacy_display')

    class Meta:
        model = ExternalAccount
        fields = ('email', 'privacy')


class UserProfileSerializer(serializers.HyperlinkedModelSerializer):
    username = serializers.Field(source='user.username')

    class Meta:
        model = UserProfile
        fields = ('username', 'is_vouched', '_url')


class UserProfileDetailedSerializer(serializers.HyperlinkedModelSerializer):
    username = serializers.Field(source='user.username')
    email = serializers.Field(source='email')
    photo = serializers.SerializerMethodField('get_photo')
    alternate_emails = AlternateEmailSerializer(many=True, source='alternate_emails')
    country = serializers.SerializerMethodField('get_country')
    region = serializers.SerializerMethodField('get_region')
    city = serializers.SerializerMethodField('get_city')
    external_accounts = ExternalAccountSerializer(many=True, source='accounts')
    languages = LanguageSerializer(many=True, source='languages')
    websites = WebsiteSerializer(many=True, source='websites')
    is_public = serializers.Field(source='is_public')
    url = serializers.SerializerMethodField('get_url')

    # Add profile URL
    class Meta:
        model = UserProfile
        fields = ('username', 'full_name', 'email', 'alternate_emails', 'bio', 'photo',
                  'ircname', 'date_mozillian', 'timezone', 'title', 'story_link', 'languages',
                  'external_accounts', 'websites', 'tshirt', 'is_public', 'is_vouched',
                  '_url', 'url', 'city', 'region', 'country')

    def _transform_privacy_wrapper(self, field):

        def _transform_privacy(obj, value):
            return {
                'value': value,
                'privacy': getattr(obj, 'get_privacy_{0}_display'.format(field))()
            }
        return _transform_privacy

    def __init__(self, *args, **kwargs):
        super(UserProfileDetailedSerializer, self).__init__(*args, **kwargs)

        # If we don't define a custom transform method and if the
        # field has a privacy setting, set the transform privacy
        # wrapper.
        for field in self.fields.keys():
            method_name = 'transform_{0}'.format(field)

            if ((not getattr(self, method_name, None) and
                 getattr(UserProfile, 'get_privacy_{0}_display'.format(field), None))):
                setattr(self, method_name, self._transform_privacy_wrapper(field))

    def get_url(self, obj):
        return absolutify(reverse('phonebook:profile_view',
                                  kwargs={'username': obj.user.username}))

    def transform_timezone(self, obj, value):
        return {
            'value': value,
            'utc_offset': obj.timezone_offset(),
            'privacy': obj.get_privacy_timezone_display(),
        }

    def transform_bio(self, obj, value):
        return {
            'value': value,
            'html': unicode(markdown(value)),
            'privacy': obj.get_privacy_bio_display(),
        }

    def get_photo(self, obj):
        return {
            'value': obj.get_photo_url('300x300'),
            '150x150': obj.get_photo_url('150x150'),
            '300x300': obj.get_photo_url('300x300'),
            '500x500': obj.get_photo_url('500x500'),
        }

    def transform_photo(self, obj, value):
        privacy_field = {'privacy': obj.get_privacy_photo_display()}
        value.update(privacy_field)
        return value

    def transform_tshirt(self, obj, value):
        return {
            'value': obj.tshirt,
            'english': obj.get_tshirt_display(),
            'privacy': obj.get_privacy_tshirt_display(),
        }

    def get_country(self, obj):
        country = obj.geo_country
        return {
            'code': country.code if country else '',
            'value': country.name if country else '',
            'privacy': obj.get_privacy_geo_country_display(),
        }

    def get_region(self, obj):
        region = obj.geo_region
        return {
            'value': region.name if region else '',
            'privacy': obj.get_privacy_geo_region_display(),
        }

    def get_city(self, obj):
        city = obj.geo_city
        return {
            'value': city.name if city else '',
            'privacy': obj.get_privacy_geo_city_display(),
        }


# Filters
class UserProfileFilter(django_filters.FilterSet):
    city = django_filters.CharFilter(name='geo_city__name')
    region = django_filters.CharFilter(name='geo_region__name')
    country = django_filters.CharFilter(name='geo_country__name')
    country_code = django_filters.CharFilter(name='geo_country__code')
    username = django_filters.CharFilter(name='user__username')
    email = django_filters.MethodFilter(action='filter_emails')
    language = django_filters.CharFilter(name='language__code')
    account = django_filters.CharFilter(name='externalaccount__identifier', distinct=True)
    group = django_filters.MethodFilter(action='filter_group')
    skill = django_filters.CharFilter(name='skills__name')

    class Meta:
        model = UserProfile
        fields = ('is_vouched', 'city', 'region', 'country', 'country_code',
                  'username', 'email', 'ircname', 'full_name', 'language',
                  'account', 'group', 'skill')

    def filter_emails(self, queryset, value):
        """Return users with email matching either primary or alternate email address"""
        qs = ExternalAccount.objects.filter(type=ExternalAccount.TYPE_EMAIL, identifier=value)
        users = qs.values_list('user__id', flat=True)
        query = Q(id__in=users) | Q(user__email=value)
        return queryset.filter(query).distinct()

    def filter_group(self, queryset, value):
        membership = GroupMembership.MEMBER
        return queryset.filter(groups__name=value, groupmembership__status=membership)


# Views
class UserProfileViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Returns a list of Mozillians respecting authorization levels
    and privacy settings.
    """
    serializer_class = UserProfileSerializer
    model = UserProfile
    filter_class = UserProfileFilter
    ordering = ('user__username',)

    def get_queryset(self):
        queryset = UserProfile.objects.complete()
        privacy_level = self.request.privacy_level
        if privacy_level == PUBLIC:
            queryset = queryset.public()

        queryset = queryset.privacy_level(privacy_level)
        return queryset

    def retrieve(self, request, pk):
        user = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = UserProfileDetailedSerializer(user, context={'request': self.request})
        return Response(serializer.data)
