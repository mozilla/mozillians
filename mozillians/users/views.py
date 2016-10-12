from django.db.models import Q
from django.contrib.auth.models import User

from dal import autocomplete

from mozillians.users.models import UserProfile


class BaseProfileAdminAutocomplete(autocomplete.Select2QuerySetView):
    """Base class for django-autocomplete-light."""

    def get_queryset(self):
        """Base queryset used only in admin.

        Return all the users who have completed their profile registration.
        """
        if not self.request.user.is_staff:
            return UserProfile.objects.none()

        qs = UserProfile.objects.complete()
        self.q_base_filter = (Q(full_name__icontains=self.q) |
                              Q(user__email__icontains=self.q) |
                              Q(user__username__icontains=self.q))

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
        self.q_base_filter = (Q(userprofile__full_name__icontains=self.q) |
                              Q(email__icontains=self.q) |
                              Q(username__icontains=self.q))

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
            qs = qs.filter(Q(full_name__icontains=self.q) |
                           Q(user__email__icontains=self.q) |
                           Q(user__username__icontains=self.q))
        return qs
