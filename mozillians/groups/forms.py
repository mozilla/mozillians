import re

from django import forms
from django.core.exceptions import ValidationError

from tower import ugettext as _
from tower import ugettext_lazy as _lazy

from mozillians.groups.helpers import stringify_groups
from mozillians.groups.models import Group


class SortForm(forms.Form):
    """Group Index Sort Form."""
    sort = forms.ChoiceField(required=False,
                             choices=(('name', _lazy(u'Group Name A-Z')),
                                      ('-num_members', _lazy(u'Most Members')),
                                      ('num_members', _lazy(u'Fewest Members'))))

    def clean_sort(self):
        if self.cleaned_data['sort'] == '':
            return 'name'
        return self.cleaned_data['sort']


class GroupWidget(forms.TextInput):

    def render(self, name, value, attrs=None):
        if not (value is None or isinstance(value, basestring)):
            value = stringify_groups(Group.objects.get(pk=v) for v in value)

        return super(GroupWidget, self).render(name, value, attrs)


class GroupField(forms.CharField):
    widget = GroupWidget

    def clean(self, value):
        """Groups are saved in lowercase because it's easy and
        consistent.

        """
        value = super(GroupField, self).clean(value)

        if not re.match(r'^[a-zA-Z0-9 .:,-]*$', value):
            raise ValidationError(_(u'Groups can only contain alphanumeric '
                                    'characters, dashes, spaces.'))

        values = [g.strip() for g in value.lower().split(',')
                  if g and ',' not in g]

        groups = []
        for g in values:
            (group, created) = Group.objects.get_or_create(name=g)

            if not group.system:
                groups.append(group)

        return groups
