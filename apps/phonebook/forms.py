import re

from django import forms
from django.utils.safestring import mark_safe

import happyforms
from tower import ugettext as _, ugettext_lazy as _lazy

from apps.groups.models import Group, Skill, Language
from apps.users.helpers import validate_username
from apps.users.models import User, UserProfile

from models import Invite

PAGINATION_LIMIT = 20

REGEX_NUMERIC = re.compile('\d+', re.IGNORECASE)


class SearchForm(happyforms.Form):
    q = forms.CharField(widget=forms.HiddenInput, required=False)
    limit = forms.CharField(widget=forms.HiddenInput, required=False)
    nonvouched_only = forms.BooleanField(label=_lazy(u'Non Vouched Only'),
                                         required=False)
    picture_only = forms.BooleanField(label=_lazy(u'Only users with photos'),
                                      required=False)

    def clean_limit(self):
        """Validate that this limit is numeric and greater than 1."""
        limit = self.cleaned_data['limit']

        if not limit:
            limit = PAGINATION_LIMIT
        elif not REGEX_NUMERIC.match(str(limit)) or int(limit) < 1:
            limit = PAGINATION_LIMIT

        return limit


class UsernameWidget(forms.widgets.TextInput):
    """A TextInput with some special markup to indicate a URL."""

    def render(self, *args, **kwargs):
        return mark_safe(u'<span class="label-text">'
                          'http://mozillians.org/ </span>%s' %
                super(UsernameWidget, self).render(*args, **kwargs))


class UserForm(forms.ModelForm):
    """Instead of just inhereting form a UserProfile model form, this
    base class allows us to also abstract over methods that have to do
    with the User object that need to exist in both Registration and
    Profile.

    """

    first_name = forms.CharField(label=_lazy(u'First Name'), max_length=30,
                                                             required=False)
    last_name = forms.CharField(label=_lazy(u'Last Name'), max_length=30,
                                                           required=True)
    username = forms.CharField(label=_lazy(u'Username'), max_length=30,
                                                         required=False)

    def clean_username(self):
        username = self.cleaned_data['username']
        if not username:
            return self.instance.user.username

        # Don't be jacking somebody's username
        # This causes a potential race condition however the worst that can
        # happen is bad UI.
        if (User.objects.filter(username=username).
            exclude(pk=self.instance.user.id).exists()):
            raise forms.ValidationError(_('This username is in use. Please try'
                                          ' another.'))

        # No funky characters in username.
        if not re.match(r'^[\w.@+-]+$', username):
            raise forms.ValidationError(_('Please use only alphanumeric'
                                          ' characters'))

        if not validate_username(username):
            raise forms.ValidationError(_('This username is not allowed, '
                                          'please choose another.'))
        return username

    def save(self):
        # First save the profile info.
        super(forms.ModelForm, self).save()

        # Then deal with the user info.
        user = self.instance.user
        user.first_name = (self.cleaned_data.get('first_name') or
                           user.first_name)
        user.last_name = self.cleaned_data.get('last_name') or user.last_name
        user.username = self.cleaned_data.get('username') or user.username
        user.save()


class ProfileForm(UserForm):
    photo = forms.ImageField(label=_lazy(u'Profile Photo'), required=False)
    photo_delete = forms.BooleanField(label=_lazy(u'Remove Profile Photo'),
                                      required=False)

    groups = forms.CharField(label=_lazy(
            u'Start typing to add a group (example: Marketing, '
            'Support, WebDev, Thunderbird)'), required=False)
    skills = forms.CharField(label=_lazy(
            u'Start typing to add a skill (example: Python, javascript, '
            'Graphic Design, User Research)'), required=False)
    languages = forms.CharField(label=_lazy(
            u'Start typing to add a language you speak (example: English, '
            'French, German)'), required=False)

    username = forms.CharField(label=_lazy(u'Username'), max_length=30,
                                                         required=False,
                                                         widget=UsernameWidget)

    class Meta:
        # Model form stuff
        model = UserProfile
        fields = ('ircname', 'website', 'bio', 'photo', 'country', 'region',
                  'city', 'allows_community_sites', 'allows_mozilla_sites')
        widgets = {'bio': forms.Textarea()}

    def clean_groups(self):
        """Groups are saved in lowercase because it's easy and
        consistent.

        """
        if not re.match(r'^[a-zA-Z0-9 .:,-]*$', self.cleaned_data['groups']):
            raise forms.ValidationError(_(u'Groups can only contain '
                                           'alphanumeric characters, dashes, '
                                           'spaces.'))

        system_groups = [g.name for g in self.instance.groups.all()
                         if g.system]

        new_groups = [g.strip()
                      for g in self.cleaned_data['groups'].lower().split(',')
                      if g and ',' not in g]

        return system_groups + new_groups

    def clean_skills(self):
        if not re.match(r'^[a-zA-Z0-9 .:,-]*$', self.cleaned_data['skills']):
            raise forms.ValidationError(_(u'Skills can only contain '
                                           'alphanumeric characters, dashes, '
                                           'spaces.'))
        return [s.strip()
                for s in self.cleaned_data['skills'].lower().split(',')
                if s and ',' not in s]

    def clean_languages(self):
        if not re.match(r'^[a-zA-Z0-9 .:,-]*$',
                        self.cleaned_data['languages']):
            raise forms.ValidationError(_(u'Languages can only contain '
                                           'alphanumeric characters, dashes, '
                                           'spaces.'))
        return [s.strip()
                for s in self.cleaned_data['languages'].lower().split(',')
                if s and ',' not in s]

    def clean(self):
        """Make sure geographic fields aren't underspecified."""
        cleaned_data = super(ProfileForm, self).clean()
        # Rather than raising ValidationErrors for the whole form, we can
        # add errors to specific fields.
        if cleaned_data['city'] and not cleaned_data['region']:
            self._errors['region'] = [_(u'You must specify a region to '
                                         'specify a city.')]
        if cleaned_data['region'] and not cleaned_data['country']:
            self._errors['country'] = [_(u'You must specify a country to '
                                         'specify a district.')]
        return cleaned_data

    def save(self):
        """Save the data to profile."""
        self.instance.set_membership(Group, self.cleaned_data['groups'])
        self.instance.set_membership(Skill, self.cleaned_data['skills'])
        self.instance.set_membership(Language, self.cleaned_data['languages'])
        super(ProfileForm, self).save()


class VouchForm(happyforms.Form):
    """Vouching is captured via a user's id."""
    vouchee = forms.IntegerField(widget=forms.HiddenInput)


class InviteForm(happyforms.ModelForm):

    def clean_recipient(self):
        recipient = self.cleaned_data['recipient']

        if User.objects.filter(email=recipient).count() > 0:
            raise forms.ValidationError(_(u'You cannot invite someone who has '
                                            'already been vouched.'))
        return recipient

    def save(self, inviter):
        invite = super(InviteForm, self).save(commit=False)
        invite.inviter = inviter
        invite.save()
        return invite

    class Meta:
        model = Invite
        exclude = ('redeemer', 'inviter')
