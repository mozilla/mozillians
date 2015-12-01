from django import forms
from django.forms.widgets import RadioSelect

import happyforms
from tower import ugettext as _
from tower import ugettext_lazy as _lazy

from mozillians.groups.models import Group


class SortForm(forms.Form):
    """Group Index Sort Form."""
    sort = forms.ChoiceField(required=False,
                             choices=(('name', _lazy(u'Name A-Z')),
                                      ('-member_count', _lazy(u'Most Members')),
                                      ('member_count', _lazy(u'Fewest Members'))))

    def clean_sort(self):
        if self.cleaned_data['sort'] == '':
            return 'name'
        return self.cleaned_data['sort']


class GroupForm(happyforms.ModelForm):

    def clean(self):
        cleaned_data = super(GroupForm, self).clean()
        accepting_new = cleaned_data.get('accepting_new_members')
        criteria = cleaned_data.get('new_member_criteria')

        if not accepting_new == 'by_request':
            cleaned_data['new_member_criteria'] = u''
        else:
            if not criteria:
                msg = _(u'You must either specify the criteria or change the '
                        'acceptance selection.')
                self._errors['new_member_criteria'] = self.error_class([msg])
                del cleaned_data['new_member_criteria']
        return cleaned_data

    class Meta:
        model = Group
        fields = ['name', 'description', 'irc_channel',
                  'website', 'wiki', 'accepting_new_members',
                  'new_member_criteria', 'terms']


class SuperuserGroupForm(GroupForm):
    """Form used by superusers (admins) when editing a group"""

    class Meta:
        model = Group
        fields = ['name',
                  'description',
                  'irc_channel',
                  'website',
                  'wiki',
                  'visible',
                  'functional_area',
                  'members_can_leave',
                  'accepting_new_members',
                  'new_member_criteria',
                  'terms'
                  ]


class MembershipFilterForm(forms.Form):
    filtr = forms.ChoiceField(required=False,
                              label='',
                              choices=(('all', _lazy(u'All')),
                                       ('members', _lazy(u'Members')),
                                       ('pending_members', _lazy(u'Pending Members'))))

    def clean_filtr(self):
        if self.cleaned_data['filtr'] == '':
            return 'all'
        return self.cleaned_data['filtr']


class TermsReviewForm(forms.Form):
    terms_accepted = forms.ChoiceField(required=True, initial=True, widget=RadioSelect,
                                       choices=[
                                           (True, _('I accept these terms.')),
                                           (False, _("I don't accept these terms."))
                                       ])
