from django import forms

import happyforms
from tower import ugettext_lazy as _lazy

from mozillians.groups.models import Group


class SortForm(forms.Form):
    """Group Index Sort Form."""
    sort = forms.ChoiceField(required=False,
                             choices=(('name', _lazy(u'Name A-Z')),
                                      ('-num_members', _lazy(u'Most Members')),
                                      ('num_members', _lazy(u'Fewest Members'))))

    def clean_sort(self):
        if self.cleaned_data['sort'] == '':
            return 'name'
        return self.cleaned_data['sort']


class GroupForm(happyforms.ModelForm):

    class Meta:
        model = Group
        fields = ['name', 'description', 'irc_channel',
                  'website', 'wiki']


class SuperuserGroupForm(happyforms.ModelForm):
    """Form used by superusers (admins) when editing a group"""
    class Meta:
        model = Group
        fields = ['name', 'description', 'irc_channel',
                  'website', 'wiki',
                  'visible',
                  'functional_area',
                  'members_can_leave',
                  'accepting_new_members',
                  ]
