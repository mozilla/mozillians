from django import forms
from django.conf import settings
from django.forms.widgets import RadioSelect

import happyforms
from dal import autocomplete
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

        # Dynamically change autocomplete widget
        if self.instance.is_access_group:
            self.fields['curators'].widget = autocomplete.ModelSelect2Multiple(
                url='users:access-group-invitation-autocomplete'
            )
        else:
            self.fields['curators'].widget = autocomplete.ModelSelect2Multiple(
                url='groups:curators-autocomplete'
            )

        self.fields['curators'].widget.choices = self.fields['curators'].choices

    def clean(self):
        cleaned_data = super(GroupCuratorsForm, self).clean()
        curators = cleaned_data.get('curators')
        # Check if group is a legacy group without curators.
        # In this case we should allow curators relation to be empty.
        group_has_curators = self.instance.pk and self.instance.curators.exists()

        error_msgs = []
        if not curators and group_has_curators:
            msg = _(u'The group must have at least one curator.')
            error_msgs.append(msg)

        if self.instance.is_access_group and not self.instance.name == settings.NDA_GROUP:
            for curator in curators:
                if not (curator.is_nda or curator.can_create_access_groups):
                    msg = _(u'Only staff and NDA members can become access group curators')
                    error_msgs.append(msg)
                    break

        if error_msgs:
            self._errors['curators'] = self.error_class(error_msgs)
        return cleaned_data

    def clean_curators(self):
        """Clean the curators field.

        If this is an access group and there is a non staff curator
        then the curators field should not be editable.
        """
        user = self.request.user
        if user and user.userprofile:
            is_community_curator = all([user,
                                        user.userprofile,
                                        user.userprofile.is_nda,
                                        not user.userprofile.can_create_access_groups])
            # If the group already exists and the curator is not staff but an NDA member
            # for an access group, then the list of curators should not editable
            group = self.instance
            if group and group.is_access_group and group.pk and is_community_curator:
                return self.instance.curators
        return self.cleaned_data['curators']

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
        # Dynamically initialize the Select2 widget
        self.fields['invites'].widget = autocomplete.ModelSelect2Multiple(
            url='users:access-group-invitation-autocomplete')
        self.fields['invites'].widget.choices = self.fields['invites'].choices
        if self.instance.pk:
            self.initial['invites'] = []

            # If the group is a TAG or is the NDA we need to query all the vouched
            # mozillians and not only staff or NDA members.
            if not self.instance.is_access_group:
                self.fields['invites'].widget = autocomplete.ModelSelect2Multiple(
                    url='groups:curators-autocomplete')
                self.fields['invites'].widget.choices = self.fields['invites'].choices
            # Force an MFAed method for NDA invitations
            elif self.instance.name == settings.NDA_GROUP:
                self.fields['invites'].widget = autocomplete.ModelSelect2Multiple(
                    url='users:nda-group-invitation-autocomplete')
                self.fields['invites'].widget.choices = self.fields['invites'].choices
                help_text = self.fields['invites'].help_text
                self.fields['invites'].help_text = (
                    help_text + _(' Only vouched users with a Multi Factor Authentication method '
                                  'enabled (GitHub or LDAP logins) can be invited.'))
            else:
                self.fields['invites'].help_text = _('Start typing the name/email/username '
                                                     'of a staff member or a member of the NDA '
                                                     'group.')

    def clean(self):
        """Custom clean method."""
        super(GroupInviteForm, self).clean()
        user = self.request.user
        is_manager = user.userprofile.is_manager
        is_curator = self.instance.curators.filter(id=user.userprofile.id).exists()

        error_msgs = []
        if not is_curator and not is_manager:
            msg = _(u'You need to be the curator of this group before inviting someone to join.')
            error_msgs.append(msg)

        if self.instance.is_access_group and not self.instance.name == settings.NDA_GROUP:
            msg = _(u'Only staff and NDA members are allowed to be invited')
            for profile in self.cleaned_data['invites']:
                if not (profile.is_nda or profile.can_create_access_groups):
                    error_msgs.append(msg)
                    break

        if error_msgs:
            self._errors['invites'] = self.error_class(error_msgs)

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


class HorizontalRadioSelect(forms.RadioSelect):
    template_name = 'widgets/horizontal_select.html'


class GroupCriteriaForm(happyforms.ModelForm):

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(GroupCriteriaForm, self).__init__(*args, **kwargs)
        # Do not show the Open option for access groups.
        if self.instance.id and self.instance.is_access_group:
            self.fields['accepting_new_members'] = forms.ChoiceField(
                choices=tuple(x for x in Group.GROUP_TYPES if x[0] != 'yes'),
                widget=HorizontalRadioSelect())

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

        if (self.instance and self.instance.is_access_group and
                cleaned_data.get('accepting_new_members') == Group.OPEN):
                msg = _(u'An access group cannot be of type Open.')
                self._errors['accepting_new_members'] = self.error_class([msg])
        return cleaned_data

    class Meta:
        model = Group
        fields = ('accepting_new_members', 'new_member_criteria',)
        widgets = {
            'accepting_new_members': HorizontalRadioSelect()
        }
        labels = {
            'accepting_new_members': _('Select Group Type')
        }


class GroupAccessForm(happyforms.ModelForm):
    """Modelform which handles the editing of access/tag groups."""

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(GroupAccessForm, self).__init__(*args, **kwargs)

    def clean(self):
        """Custom clean method."""
        super(GroupAccessForm, self).clean()
        user = getattr(self.request, 'user', None)
        if ((not user or not user.userprofile.can_create_access_groups) and
                self.cleaned_data['is_access_group']):
            msg = _(u'You do not have the permissions to provision an access group.')
            self._errors['is_access_group'] = self.error_class([msg])

        if (self.instance.id and self.instance.accepting_new_members == Group.OPEN and
                self.cleaned_data['is_access_group']):
            msg = _(u'An access group must be of type Reviewed or Closed.')
            self._errors['is_access_group'] = self.error_class([msg])

        return self.cleaned_data

    class Meta:
        model = Group
        fields = ('is_access_group',)
        widgets = {
            'is_access_group': HorizontalRadioSelect()
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


class GroupCreateForm(GroupAccessForm):

    def __init__(self, *args, **kwargs):
        super(GroupCreateForm, self).__init__(*args, **kwargs)
        user = getattr(self.request, 'user', None)
        if not user or not user.userprofile.can_create_access_groups:
            self.fields['is_access_group'].widget = forms.HiddenInput()

    def clean(self):
        """Custom clean method.

        Check that only closed/reviewed groups can be access groups.
        """
        cdata = super(GroupCreateForm, self).clean()
        if cdata['is_access_group'] and cdata['accepting_new_members'] == Group.OPEN:
            msg = _(u'Group must be of type Reviewed or Closed for Access Groups.')
            self._errors['is_access_group'] = self.error_class([msg])
        return cdata

    class Meta:
        model = Group
        fields = ('name', 'accepting_new_members', 'is_access_group',)
        widgets = {
            'accepting_new_members': HorizontalRadioSelect(),
            'is_access_group': HorizontalRadioSelect()
        }
        labels = {
            'accepting_new_members': _('Group type')
        }
