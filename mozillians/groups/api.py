from django.db.models import Sum

from tastypie.resources import ModelResource
from tastypie.serializers import Serializer

from tastypie import fields
from mozillians.api.authenticators import AppAuthentication
from mozillians.api.authorisers import MozillaOfficialAuthorization
from mozillians.api.resources import (AdvancedSortingResourceMixIn,
                                      ClientCacheResourceMixIn)
from mozillians.api.paginator import Paginator
from mozillians.groups.models import Group, Language, Skill


class GroupBaseResource(AdvancedSortingResourceMixIn, ClientCacheResourceMixIn,
                        ModelResource):
    number_of_members = fields.IntegerField(attribute='number_of_members',
                                            readonly=True)

    class Meta:
        authentication = AppAuthentication()
        authorization = MozillaOfficialAuthorization()
        cache_control = {'max-age': 0}
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get']
        paginator_class = Paginator
        serializer = Serializer(formats=['json', 'jsonp'])
        fields = ['id', 'name', 'number_of_members']
        ordering = ['id', 'name', 'number_of_members']
        default_order = ['id']


class GroupResource(GroupBaseResource):

    class Meta(GroupBaseResource.Meta):
        resource_name = 'groups'
        # This Sum hack counts the number of 1's in database, only
        # works with MySQL because it stores booleans as 0s and 1s
        queryset = (Group.objects
                    .annotate(number_of_members=Sum('members__is_vouched'))
                    .filter(number_of_members__gt=0))


class LanguageResource(GroupBaseResource):

    class Meta(GroupBaseResource.Meta):
        resource_name = 'languages'
        queryset = (Language.objects
                    .annotate(number_of_members=Sum('members__is_vouched'))
                    .filter(number_of_members__gt=0))


class SkillResource(GroupBaseResource):

    class Meta(GroupBaseResource.Meta):
        resource_name = 'skills'
        queryset = (Skill.objects
                    .annotate(number_of_members=Sum('members__is_vouched'))
                    .filter(number_of_members__gt=0))
