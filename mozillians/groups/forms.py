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
    def clean(self):
        cleaned_data = super(SuperuserGroupForm, self).clean()
        accepting_new = cleaned_data.get('accepting_new_members')
        criteria = cleaned_data.get('new_member_criteria')

        if (accepting_new == 'by_request' and len(criteria) == 0):
            msg = _lazy(u'You must either specify the criteria or change the acceptance selection.')
            self._errors['new_member_criteria'] = self.error_class([msg])
            del cleaned_data['new_member_criteria']

        return cleaned_data

    class Meta:
        model = Group
        fields = ['name', 'description', 'irc_channel',
                  'website', 'wiki',
                  'visible',
                  'functional_area',
                  'members_can_leave',
                  'accepting_new_members',
                  'new_member_criteria',
                  ]
