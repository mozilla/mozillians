from django.db.models import Q
from django.contrib.auth.models import User

from dal import autocomplete

from mozillians.common.templatetags.helpers import get_object_or_none
from mozillians.groups.models import Group
from mozillians.users.models import UserProfile


class BaseProfileAutocompleteQueryset(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        """Base queryset used only in admin.

        Return all the users who have completed their profile registration.
        """

        qs = UserProfile.objects.all()
        self.q_base_filter = (Q(full_name__icontains=self.q) |
                              Q(user__email__icontains=self.q) |
                              Q(user__username__icontains=self.q))

        if self.q:
            qs = qs.filter(self.q_base_filter)
        return qs


class BaseProfileAdminAutocomplete(BaseProfileAutocompleteQueryset):
    """Base class for django-autocomplete-light."""

    def get_queryset(self):
        """Base queryset used only in admin.

        Return all the users who have completed their profile registration.
        """
        if not self.request.user.is_staff:
            return UserProfile.objects.none()

        return super(BaseProfileAdminAutocomplete, self).get_queryset().complete()


class UsersAdminAutocomplete(BaseProfileAutocompleteQueryset):
    """Base class for django-autocomplete-light."""

    def get_queryset(self):
        """Base queryset used only in admin.

        Return all the users who have completed their profile registration.
        """
        if not self.request.user.is_staff:
            return User.objects.none()
        return super(UsersAdminAutocomplete, self).get_queryset()


class VoucherAutocomplete(BaseProfileAdminAutocomplete):

    def get_queryset(self):
        """Augment base queryset by returning only users who can vouch."""
        return super(VoucherAutocomplete, self).get_queryset().complete().filter(can_vouch=True)


class VouchedAutocomplete(BaseProfileAdminAutocomplete):

    def get_queryset(self):
        """Augment base queryset by returning only vouched users."""
        return super(VouchedAutocomplete, self).get_queryset().vouched()


class CuratorsAutocomplete(BaseProfileAutocompleteQueryset):

    def get_queryset(self):
        """Augment queryset by returning only vouched users."""

        # Allow only vouched users to perform this query.
        if not self.request.user.userprofile.is_vouched:
            return UserProfile.objects.none()
        # return only vouched users
        qs = super(CuratorsAutocomplete, self).get_queryset().vouched()
        # filter out current curators of the
        group = get_object_or_none(Group, name=self.forwarded.get('name'))
        return qs.exclude(id__in=group.curators.all())


class InvitesAutocomplete(BaseProfileAutocompleteQueryset):

    def get_queryset(self):
        """Augment queryset by returning only vouched users."""

        # Allow only vouched users to perform this query.
        if not self.request.user.userprofile.is_vouched:
            return UserProfile.objects.none()
        qs = super(InvitesAutocomplete, self).get_queryset().vouched()
        group = get_object_or_none(Group, name=self.forwarded.get('name'))
        curators_ids = group.curators.all().values_list('id', flat=True)
        invites_ids = group.invited.all().values_list('redeemer', flat=True)
        return qs.exclude(id__in=curators_ids).exclude(id__in=invites_ids)
