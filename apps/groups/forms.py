import re

from django import forms

from .helpers import stringify_groups
from .models import Group


class GroupWidget(forms.TextInput):
    def render(self, name, value, attrs=None):
        print "THE VALUE", value
        if value is not None and not isinstance(value, basestring):
            value = stringify_groups(Group.objects.get(pk=v) for v in value)

        return super(GroupWidget, self).render(name, value, attrs)


class GroupField(forms.CharField):
    widget = GroupWidget

    def clean(self, value):
        """Groups are saved in lowercase because it's easy and consistent."""
        value = super(GroupField, self).clean(value)

        if not re.match(r'^[a-zA-Z0-9 .:,-]*$', value):
            raise forms.ValidationError(_(u'Groups can only contain '
                                          'alphanumeric characters, dashes, '
                                          'spaces.'))

        values = [g.strip() for g in (value.lower().split(','))
                if g and ',' not in g]

        groups = []
        for g in values:
            (group, created) = Group.objects.get_or_create(name=g)

            if not group.system:
                groups.append(group)

        return groups
