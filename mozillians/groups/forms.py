from django import forms
from django.forms.widgets import RadioSelect

import happyforms
from dal import autocomplete
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy as _lazy

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
    invalidation_days = forms.IntegerField(
        widget=forms.NumberInput(attrs={'placeholder': 'days'}),
        min_value=1,
        label='Membership will expire after',
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super(GroupForm, self).__init__(*args, **kwargs)
        self.fields['curators'].required = False
        self.fields['curators'].error_messages['required'] = (
            _(u'The group must have at least one curator.'))
        if not self.instance.pk:
            self.fields['curators'].required = True
        self.fields['curators'].help_text = (u'Start typing the name/email/username '
                                             'of a Mozillian.')

    def clean(self):
        cleaned_data = super(GroupForm, self).clean()
        accepting_new = cleaned_data.get('accepting_new_members')
        criteria = cleaned_data.get('new_member_criteria')
        curators = cleaned_data.get('curators')

        if not accepting_new == 'by_request':
            cleaned_data['new_member_criteria'] = u''
        else:
            if not criteria:
                msg = _(u'You must either specify the criteria or change the '
                        'acceptance selection.')
                self._errors['new_member_criteria'] = self.error_class([msg])
                del cleaned_data['new_member_criteria']

        # Check if group is a legacy group without curators.
        # In this case we should allow curators relation to be empty.
        group_has_curators = self.instance.pk and self.instance.curators.exists()

        if not curators and group_has_curators:
            msg = _(u'The group must have at least one curator.')
            self._errors['curators'] = self.error_class([msg])

        return cleaned_data

    def save(self, *args, **kwargs):
        """Custom save method to add multiple curators."""
        obj = super(GroupForm, self).save(*args, **kwargs)

        for curator in self.cleaned_data['curators']:
            if not obj.has_member(curator):
                obj.add_member(curator)
        return obj

    class Meta:
        model = Group
        fields = ('name', 'description', 'irc_channel', 'website', 'wiki',
                  'accepting_new_members', 'new_member_criteria', 'terms', 'curators',
                  'invalidation_days',)
        widgets = {
            'curators': autocomplete.ModelSelect2Multiple(url='groups:curators-autocomplete')
        }


class SuperuserGroupForm(GroupForm):
    """Form used by superusers (admins) when editing a group"""

    class Meta(GroupForm.Meta):
        fields = GroupForm.Meta.fields + ('visible', 'functional_area', 'members_can_leave',)


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
