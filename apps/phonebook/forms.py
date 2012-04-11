import re
from urlparse import urlparse

from django import forms
from django.conf import settings
from django.core.urlresolvers import resolve
from django.utils.safestring import mark_safe

import happyforms
from tower import ugettext as _, ugettext_lazy as _lazy

from groups.models import Group, Skill
from groups.helpers import stringify_groups
from phonebook.models import Invite
from users.models import User, UserProfile


PAGINATION_LIMIT = 20

REGEX_NUMERIC = re.compile('\d+', re.IGNORECASE)


class SearchForm(happyforms.Form):
    q = forms.CharField(widget=forms.HiddenInput, required=True)
    limit = forms.CharField(widget=forms.HiddenInput, required=False)
    nonvouched_only = forms.BooleanField(required=False)

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

    def __init__(self, *args, **kwargs):
        """Add in initial values"""
        instance = kwargs.get('instance')
        if instance:
            user = instance.user
            initial = kwargs.get('initial', {})
            initial.update(
                first_name=user.first_name,
                last_name=user.last_name)
            if not user.username.startswith('u/'):
                initial.update(username=user.username)
            kwargs['initial'] = initial

        super(UserForm, self).__init__(*args, **kwargs)

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

    class Meta:
        # Model form stuff
        model = UserProfile
        fields = ('ircname', 'website', 'bio', 'photo')
        widgets = {
            'bio': forms.Textarea()
        }

    def __init__(self, *args, **kwargs):
        """Add in initial values"""
        instance = kwargs.get('instance')
        if instance:
            initial = kwargs.get('initial', {})
            initial.update(
                groups=stringify(instance, 'groups'),
                skills=stringify(instance, 'skills'),)
            kwargs['initial'] = initial

        super(ProfileForm, self).__init__(*args, **kwargs)

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

def stringify(profile, obj_name):
    """
    Takes a profile and a type (probably skill or group) and returns its
    stringified objects
    """
    return stringify_groups(getattr(profile, obj_name).all().order_by('name'))
