from django import forms
from django.forms.widgets import RadioSelect

import happyforms
from tower import ugettext as _
from tower import ugettext_lazy as _lazy

from mozillians.groups.models import Group
from mozillians.users.models import UserProfile


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
    curators = forms.CharField(label='Curators',
                               help_text=_lazy(u'Start typing to add a curator '
                                               '(example: John Doe, )'))
    invalidation_days = forms.IntegerField(
        widget=forms.NumberInput(attrs={'placeholder': 'days'}),
        min_value=1,
        label='Membership will expire after',
        required=False
    )

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

    def clean_curators(self):
        """ Clean the list of possible curators."""
        msg = ''
        possible_curators = self.cleaned_data.get('curators').split(',')
        for full_name in possible_curators:
            # Make sure that the user is vouched!
            if not UserProfile.objects.filter(full_name=full_name, is_vouched=True).exists():
                msg = _('The name "{0}" you chose does not '
                        'belong to a vouched Mozillian.'.format(full_name))
                break

        if not possible_curators:
            msg = _(u'The group must have at least one curator.')
        if msg:
            raise forms.ValidationError(msg)
        return possible_curators

    def save(self, *args, **kwargs):
        """Custom save method to add multiple curators."""
        obj = super(GroupForm, self).save()

        # Add the curators in the m2m field
        obj.curators.clear()
        for curator in self.cleaned_data['curators']:
            cur_obj = UserProfile.objects.get(full_name=curator)
            obj.curators.add(cur_obj)
            # Ensure that all curators are members of the group
            if not obj.has_member(cur_obj):
                obj.add_member(cur_obj)
        return obj

    class Meta:
        model = Group
        fields = ['name', 'description', 'irc_channel',
                  'website', 'wiki', 'accepting_new_members',
                  'new_member_criteria', 'terms', 'invalidation_days']


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
                  'terms',
                  'invalidation_days']


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
