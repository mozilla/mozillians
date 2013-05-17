import re

from django import forms
from django.utils.safestring import mark_safe

import happyforms
from django.utils import simplejson
from product_details import product_details
from tower import ugettext as _, ugettext_lazy as _lazy

from apps.groups.models import Group, Skill, Language
from apps.users.helpers import validate_username
from apps.users.models import User, UserProfile, MessengerName

from models import Invite

PAGINATION_LIMIT = 20
REGEX_NUMERIC = re.compile('\d+', re.IGNORECASE)


class SearchForm(happyforms.Form):
    q = forms.CharField(widget=forms.HiddenInput, required=False)
    limit = forms.CharField(widget=forms.HiddenInput, required=False)
    include_non_vouched = forms.BooleanField(
        label=_lazy(u'Include non-vouched'), required=False)

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
                          'http://mozillians.org/u/ </span>%s' %
                super(UsernameWidget, self).render(*args, **kwargs))


class UserForm(happyforms.ModelForm):
    """Instead of just inhereting form a UserProfile model form, this
    base class allows us to also abstract over methods that have to do
    with the User object that need to exist in both Registration and
    Profile.

    """
    username = forms.CharField(label=_lazy(u'Username'),
                               max_length=30, required=False)

    class Meta:
        model = User
        fields = ['username']
        widgets = {'username': UsernameWidget()}

    def clean_username(self):
        username = self.cleaned_data['username']
        if not username:
            return self.instance.username

        # Don't be jacking somebody's username
        # This causes a potential race condition however the worst that can
        # happen is bad UI.
        if (User.objects.filter(username=username).
            exclude(pk=self.instance.id).exists()):
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


class BaseProfileForm(happyforms.ModelForm):
    photo = forms.ImageField(label=_lazy(u'Profile Photo'), required=False)
    photo_delete = forms.BooleanField(label=_lazy(u'Remove Profile Photo'),
                                      required=False)

    skills = forms.CharField(
        label=_lazy(u'Start typing to add a skill (example: Python, '
                    'javascript, Graphic Design, User Research)'),
        required=False)
    languages = forms.CharField(
        label=_lazy(u'Start typing to add a language you speak (example: '
                    'English, French, German)'), required=False)

    class Meta:
        # Model form stuff
        model = UserProfile
        fields = ('full_name', 'ircname', 'website', 'bio', 'photo', 'country',
                  'region', 'city', 'allows_community_sites',
                  'allows_mozilla_sites', 'privacy_photo', 'privacy_full_name',
                  'privacy_ircname', 'privacy_messenger_names', 'privacy_email', 'privacy_website',
                  'privacy_bio', 'privacy_city', 'privacy_region',
                  'privacy_country', 'privacy_groups', 'privacy_skills',
                  'privacy_languages')
        widgets = {'bio': forms.Textarea()}

    def __init__(self, *args, **kwargs):
        locale = kwargs.pop('locale', 'en-US')

        super(BaseProfileForm, self).__init__(*args, **kwargs)
        country_list = product_details.get_regions(locale).items()
        country_list = sorted(country_list, key=lambda country: country[1])
        country_list.insert(0, ('', '----'))
        self.fields['country'].choices = country_list

    def clean_skills(self):
        if not re.match(r'^[a-zA-Z0-9 .:,-]*$', self.cleaned_data['skills']):
            raise forms.ValidationError(_(u'Skills can only contain '
                                           'alphanumeric characters, dashes, '
                                           'spaces.'))
        skills = self.cleaned_data['skills']
        return filter(lambda x: x,
                      map(lambda x: x.strip() or False,
                          skills.lower().split(',')))

    def clean_languages(self):
        if not re.match(r'^[a-zA-Z0-9 .:,-]*$',
                        self.cleaned_data['languages']):
            raise forms.ValidationError(_(u'Languages can only contain '
                                           'alphanumeric characters, dashes, '
                                           'spaces.'))
        languages = self.cleaned_data['languages']

        return filter(lambda x: x,
                      map(lambda x: x.strip() or False,
                          languages.lower().split(',')))

    def clean(self):
        """Make sure geographic fields aren't underspecified."""
        cleaned_data = super(BaseProfileForm, self).clean()
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
        super(BaseProfileForm, self).save()


class ProfileForm(BaseProfileForm):
    groups = forms.CharField(
        label=_lazy(u'Start typing to add a group (example: Marketing, '
                    'Support, WebDev, Thunderbird)'), required=False)


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
        groups = self.cleaned_data['groups']
        new_groups = filter(lambda x: x,
                            map(lambda x: x.strip() or False,
                                groups.lower().split(',')))

        return system_groups + new_groups


class RegisterForm(BaseProfileForm):
    optin = forms.BooleanField(
        label=_lazy(u"I'm okay with you handling this info as you "
                    u"explain in Mozilla's privacy policy."),
        widget=forms.CheckboxInput(attrs={'class': 'checkbox'}),
        required=True)

    groups = forms.ModelMultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        label=_lazy(u'Please indicate the functional areas you are currently '
                    'contributing to or would like to contribute to:'),
        queryset=Group.get_curated(), required=False)

    class Meta:
        # Model form stuff
        model = UserProfile
        fields = ('full_name', 'ircname', 'website', 'bio', 'photo',
                  'country', 'region', 'city')
        exclude = ('display_name', )
        widgets = {'bio': forms.Textarea()}


class VouchForm(happyforms.Form):
    """Vouching is captured via a user's id."""
    vouchee = forms.IntegerField(widget=forms.HiddenInput)


class InviteForm(happyforms.ModelForm):

    def clean_recipient(self):
        recipient = self.cleaned_data['recipient']
        if User.objects.filter(email=recipient,
                               userprofile__is_vouched=True).exists():
            raise forms.ValidationError(_(u'You cannot invite someone who '
                                          'has already been vouched.'))
        return recipient

    class Meta:
        model = Invite
        exclude = ('redeemer', 'inviter')

class MessengerForm(happyforms.ModelForm):
    name = forms.CharField(
        required=False,
        label=_lazy(u'IM Name'))
    service = forms.ChoiceField(
        choices = MessengerName.choices(),
        required=False,
        label=_lazy(u'IM Service'))
    names = forms.CharField(widget=forms.HiddenInput, required=False)
    def clean_names(self):
        try:
            names = simplejson.loads(self.cleaned_data['names'])
            return names
        except:
            return ''

    class Meta:
        model = MessengerName
        fields = ('name', 'service')

    def save(self):
        self.instance.set_messengers(self.cleaned_data['names'])
        super(MessengerForm, self).save()
