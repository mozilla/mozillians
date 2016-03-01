from django.db.models import Q
from django.contrib.auth.models import User

from dal import autocomplete


class CoordinatorAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):

        if not self.request.user.is_staff:
            return User.objects.none()

        qs = User.objects.exclude(userprofile__full_name='')

        if self.q:

            qs = qs.filter(Q(userprofile__full_name__icontains=self.q) |
                           Q(email__icontains=self.q) |
                           Q(username__icontains=self.q))
        return qs
