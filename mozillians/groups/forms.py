from django import forms
from django.core.exceptions import ValidationError

import happyforms
from tower import ugettext as _
from tower import ugettext_lazy as _lazy

from mozillians.groups.models import Group, GroupAlias


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

    def clean_name(self):
        """Verify that name is unique in ALIAS_MODEL.

        We have to duplicate code here and in
        models.GroupBase.clean due to bug
        https://code.djangoproject.com/ticket/16986. To update when we
        upgrade to Django 1.7.

        """
        name = self.cleaned_data['name']
        query = GroupAlias.objects.filter(name=name)
        if self.instance.pk:
            query = query.exclude(alias=self.instance)
        if query.exists():
            raise ValidationError(_('Group with this Name already exists.'))
        return name

    class Meta:
        model = Group
        fields = ['name', 'description', 'irc_channel',
                  'website', 'wiki']


class SuperuserGroupForm(GroupForm):
    """Form used by superusers (admins) when editing a group"""
    def clean(self):
        cleaned_data = super(SuperuserGroupForm, self).clean()
        accepting_new = cleaned_data.get('accepting_new_members')
        criteria = cleaned_data.get('new_member_criteria')

        if not accepting_new == 'by_request':
            cleaned_data['new_member_criteria'] = u''
        else:
            if not criteria:
                msg = _(u'You must either specify the criteria or change the acceptance selection.')
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
