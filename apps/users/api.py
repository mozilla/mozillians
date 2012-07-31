from datetime import datetime

from tastypie import fields
from tastypie.authentication import Authentication
from tastypie.authorization import ReadOnlyAuthorization
from tastypie.resources import ModelResource, ALL, ALL_WITH_RELATIONS

from common.api import HTMLSerializer
from users.models import UserProfile


class VouchedAuthentication(Authentication):
    """
    Api Authentication that only lets in authenticated and vouched users.
    """
    def is_authenticated(self, request, **kwargs):
        user = request.user
        if user.is_authenticated() and user.get_profile().is_vouched:
            return True

        return False

    def get_identifier(self, request):
        return request.user.username

class PaidStaffAuthentication(Authentication):
    """
    API Authentication that only lets in paid staff users
    """
    def is_authenticated(self, request, **kwargs):
        user = request.user
        if (user.is_authenticated() and
                user.get_profile().groups.filter(name='staff')):
            return True

        return False

    def get_identifier(self,request):
        return request.user.username

"""
class UserProfileResource(ModelResource):
    email = fields.CharField(attribute='user__email', null=True, readonly=True)

    class Meta:
        queryset = UserProfile.objects.select_related()
        authentication = PaidStaffAuthentication()
        authorization = ReadOnlyAuthorization()
        serializer = HTMLSerializer()
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get']
        resource_name = 'users'
        filtering = {
		    'email': ('exact'),
                    'display_name': ('exact', 'contains', 'startswith'),
                    'ircname': ('exact', 'contains', 'startswith'),
                }

    def get_object_list(self, request):
        if 'updated' in request.GET:
            try:
                time = datetime.fromtimestamp(int(request.GET.get('updated')))
            except TypeError:
                pass
            else:
                return (super(UserProfileResource, self)
                        .get_object_list(request)
                        .filter(last_updated__gt=time))

        return super(UserProfileResource, self).get_object_list(request)
"""

class VouchedResource(ModelResource):
    email = fields.CharField(attribute='user__email', null=True, readonly=True)

    class Meta:
        queryset = UserProfile.objects.all()
        authentication = VouchedAuthentication()
        authorization = ReadOnlyAuthorization()
        serializer = HTMLSerializer()
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get']
        resource_name = 'vouched'
        fields = ['is_vouched']
        filtering = {
                    'email' : ('exact'),
	        }
