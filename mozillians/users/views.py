from django.db.models import Q

from dal import autocomplete

from mozillians.users.models import UserProfile


class BaseProfileAdminAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        if not self.request.user.is_staff:
            return UserProfile.objects.none()

        qs = UserProfile.objects.complete()
        self.q_base_filter = (Q(full_name__icontains=self.q) |
                              Q(user__email__icontains=self.q) |
                              Q(user__username__icontains=self.q))

        if self.q:
            qs = qs.filter(self.q_base_filter)
        return qs


class VoucherAutocomplete(BaseProfileAdminAutocomplete):

    def get_queryset(self):
        qs = super(VoucherAutocomplete, self).get_queryset().filter(can_vouch=True)

        if self.q:
            qs = qs.filter(self.q_base_filter)
        return qs


class VouchedAutocomplete(BaseProfileAdminAutocomplete):

    def get_queryset(self):
        qs = super(VouchedAutocomplete, self).get_queryset().vouched()

        if self.q:
            qs = qs.filter(self.q_base_filter)
        return qs
