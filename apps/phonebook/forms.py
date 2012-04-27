import re
from urlparse import urlparse

from django import forms
from django.conf import settings
from django.core.urlresolvers import resolve
from django.utils.safestring import mark_safe

import happyforms
from tower import ugettext as _, ugettext_lazy as _lazy

from phonebook.models import Invite
from groups.models import Group, Skill
from users.models import User, UserProfile


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
        """Validate that this limit is numeric and greater than 1"""
        limit = self.cleaned_data['limit']

        if not limit:
            limit = PAGINATION_LIMIT
        elif not REGEX_NUMERIC.match(str(limit)) or int(limit) < 1:
            limit = PAGINATION_LIMIT

        return limit


class UsernameWidget(forms.widgets.Input):
    type = 'text'

    def render(self, *args, **kwargs):
        return mark_safe(u'<span class="label-text">'
                          'http://mozillians.org/ </span>%s' %
                super(UsernameWidget, self).render(*args, **kwargs))


class UserForm(forms.ModelForm):
    """
    Instead of just inhereting form a UserProfile model form, this base class
    allows us to also abstract over methods that have to do with the User
    object that need to exist in both Registration and Profile.
    """

    first_name = forms.CharField(label=_lazy(u'First Name'), max_length=30,
                                                             required=False)
    last_name = forms.CharField(label=_lazy(u'Last Name'), max_length=30,
                                                           required=True)
    username = forms.CharField(label=_lazy(u'Username'), max_length=30,
                                                         required=False)

    def clean_username(self):
        username = self.cleaned_data['username']
        # If you don't submit a username, you aren't changing it so you're cool
        if not username:
            return None

        # Don't be jacking somebody's username
        # This causes a potential race condition however the worst that can
        # happen is bad UI.
        if (User.objects.filter(username=username) and
                username != self.instance.user.username):
            raise forms.ValidationError(_('This username is in use. Please try'
                                          ' another.'))

        # No funky characters in username.
        if not re.match(r'^[\w.@+-]+$', username):
            raise forms.ValidationError(_('Please use only alphanumeric'
                                          ' characters'))

        if username not in settings.USERNAME_BLACKLIST:
            # TODO: we really should use middleware to handle the extra slashes
            # Check what can resolve the username (with/without trailing '/').
            # The last thing this can match for is profile.
            r = resolve(urlparse('/' + username)[2])
            # Check to make sure that only profile has been resolved for.
            if r.url_name == 'profile':
                return username

        raise forms.ValidationError(_('This username is reserved, please'
                                      ' choose another.'))

    def save(self, user):
        # First save the profile info.
        d = self.cleaned_data
        super(forms.ModelForm, self).save()

        # Then deal with the user info.
        d = self.cleaned_data
        user.first_name = d['first_name']
        user.last_name = d['last_name']
        if d['username']:
            user.username = d['username']
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

    username = forms.CharField(label=_lazy(u'Username'), max_length=30,
                                                         required=False,
                                                         widget=UsernameWidget)

    #: L10n: Street address; not entire address
    street = forms.CharField(label=_lazy(u'Address'), required=False)
    city = forms.CharField(label=_lazy(u'City'), required=False)
    # TODO: Add validation of states/provinces/etc. for known/large countries.
    province = forms.CharField(label=_lazy(u'Province/State'), required=False)
    # TODO: Add list of countries.
    country = forms.CharField(label=_lazy(u'Country'), required=False)
    postal_code = forms.CharField(label=_lazy(u'Postal/Zip Code'),
                                  required=False)

    class Meta:
        # Model form stuff
        model = UserProfile
        fields = ('ircname', 'website', 'bio', 'photo')
        widgets = {
            'bio': forms.Textarea()
        }

    def clean_groups(self):
        """Groups are saved in lowercase because it's easy and consistent."""
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

    def save(self, request):
        """Save the data to profile."""
        self.instance.set_membership(Group, self.cleaned_data['groups'])
        self.instance.set_membership(Skill, self.cleaned_data['skills'])
        super(ProfileForm, self).save(request.user)


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
