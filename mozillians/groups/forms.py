from django import forms
from django.forms.widgets import RadioSelect

import happyforms
from dal import autocomplete
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy as _lazy

from mozillians.groups.models import Group, Invite
from mozillians.groups.tasks import notify_redeemer_invitation


MAX_INVALIDATION_DAYS = 2 * 365


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


class GroupBasicForm(happyforms.ModelForm):
    """Model Form for the minimum information that a group needs."""
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(GroupBasicForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Group
        fields = ('name', 'description', 'irc_channel', 'website', 'wiki',)


class GroupCuratorsForm(happyforms.ModelForm):
    """Model Form for adding group curators."""

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(GroupCuratorsForm, self).__init__(*args, **kwargs)
        self.fields['curators'].required = False
        self.fields['curators'].error_messages['required'] = (
            _(u'The group must have at least one curator.'))
        if not self.instance.pk:
            self.fields['curators'].required = True
        self.fields['curators'].help_text = _('Start typing the name/email/username of '
                                              'a vouched Mozillian.')

    def clean(self):
        cleaned_data = super(GroupCuratorsForm, self).clean()
        curators = cleaned_data.get('curators')
        # Check if group is a legacy group without curators.
        # In this case we should allow curators relation to be empty.
        group_has_curators = self.instance.pk and self.instance.curators.exists()

        if not curators and group_has_curators:
            msg = _(u'The group must have at least one curator.')
            self._errors['curators'] = self.error_class([msg])

        return cleaned_data

    def save(self, *args, **kwargs):
        """Custom save method to add multiple curators."""
        obj = super(GroupCuratorsForm, self).save(*args, **kwargs)

        for curator in self.cleaned_data['curators']:
            if not obj.has_member(curator):
                obj.add_member(curator)
        return obj

    class Meta:
        model = Group
        fields = ('curators',)
        widgets = {
            'curators': autocomplete.ModelSelect2Multiple(url='groups:curators-autocomplete')
        }


class GroupTermsExpirationForm(happyforms.ModelForm):
    """Model Form for handling group terms and expiration period."""
    invalidation_days = forms.IntegerField(
        widget=forms.NumberInput(attrs={'placeholder': 'days'}),
        min_value=1,
        label='Membership will expire after',
        required=False,
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(GroupTermsExpirationForm, self).__init__(*args, **kwargs)

    def clean(self):
        super(GroupTermsExpirationForm, self).clean()
        # Max invalidation period is 2 years
        if self.cleaned_data['invalidation_days'] > MAX_INVALIDATION_DAYS:
            msg = _(u'The maximum expiration date for a group cannot exceed two years.')
            self._errors['invalidation_days'] = self.error_class([msg])

        return self.cleaned_data

    class Meta:
        model = Group
        fields = ('terms', 'invalidation_days',)


class GroupInviteForm(happyforms.ModelForm):
    """Model form to handle the invites to a group."""

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(GroupInviteForm, self).__init__(*args, **kwargs)
        self.fields['invites'].required = False
        self.fields['invites'].help_text = _('Start typing the name/email/username '
                                             'of a vouched Mozillian.')
        if self.instance.pk:
            self.initial['invites'] = []

    def clean(self):
        """Custom clean method."""
        super(GroupInviteForm, self).clean()
        user = self.request.user
        is_manager = user.userprofile.is_manager
        is_curator = self.instance.curators.filter(id=user.userprofile.id).exists()
        if not is_curator and not is_manager:
            msg = _(u'You need to be the curator of this group before inviting someone to join.')
            self._errors['invites'] = self.error_class([msg])
            del self.cleaned_data['invites']
        return self.cleaned_data

    def save(self, *args, **kwargs):
        """Custom save method to add data to the through model."""

        for profile in self.cleaned_data['invites']:
            if not Invite.objects.filter(group=self.instance, redeemer=profile).exists():
                # Create the Invite objects
                invite, created = Invite.objects.get_or_create(
                    group=self.instance, redeemer=profile, inviter=self.request.user.userprofile)
                # Shoot an email
                notify_redeemer_invitation.delay(invite.pk, self.instance.invite_email_text)

    class Meta:
        model = Group
        fields = ('invites',)
        widgets = {
            'invites': autocomplete.ModelSelect2Multiple(url='groups:curators-autocomplete')
        }


class GroupCustomEmailForm(happyforms.ModelForm):
    """Model form to handle the custom text sent to the invites."""

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(GroupCustomEmailForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Group
        fields = ('invite_email_text',)


class GroupAdminForm(happyforms.ModelForm):
    """Model form to administrate a group."""
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(GroupAdminForm, self).__init__(*args, **kwargs)

    def clean(self):
        """Custom clean method."""
        super(GroupAdminForm, self).clean()
        profile = self.request.user.userprofile

        if not profile.is_manager:
            msg = _(u'You need to be the administrator of this group in order to '
                    'edit this section.')
            raise forms.ValidationError(msg)
        return self.cleaned_data

    class Meta:
        model = Group
        fields = ('visible', 'members_can_leave', 'functional_area',)


class HorizontalRadioRenderer(forms.RadioSelect.renderer):
    def render(self):
        return mark_safe(u'\n'.join([u'%s\n' % w for w in self]))


class GroupCriteriaForm(happyforms.ModelForm):

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(GroupCriteriaForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(GroupCriteriaForm, self).clean()
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
        fields = ('accepting_new_members', 'new_member_criteria',)
        widgets = {
            'accepting_new_members': forms.RadioSelect(renderer=HorizontalRadioRenderer)
        }
        labels = {
            'accepting_new_members': _('Select Group Type')
        }


class MembershipFilterForm(forms.Form):
    filtr = forms.ChoiceField(required=False,
                              label='',
                              choices=(('all', _lazy(u'All')),
                                       ('members', _lazy(u'Members')),
                                       ('pending_members', _lazy(u'Pending Members')),
                                       ('pending_terms', _lazy(u'Pending Terms')),
                                       ('needs_renewal', _lazy(u'Renewals'))))

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


class GroupCreateForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ('name', 'accepting_new_members',)
        widgets = {
            'accepting_new_members': forms.RadioSelect(renderer=HorizontalRadioRenderer)
        }
        labels = {
            'accepting_new_members': _('Group type')
        }
