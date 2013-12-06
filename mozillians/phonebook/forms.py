import re
from cStringIO import StringIO
from datetime import datetime

from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import UploadedFile
from django.forms.models import inlineformset_factory

import happyforms
from PIL import Image
from product_details import product_details
from tower import ugettext as _, ugettext_lazy as _lazy

from mozillians.groups.models import Language, Skill
from mozillians.phonebook.models import Invite
from mozillians.phonebook.validators import validate_username
from mozillians.phonebook.widgets import MonthYearWidget
from mozillians.users.models import ExternalAccount, UserProfile


REGEX_NUMERIC = re.compile('\d+', re.IGNORECASE)


class ExternalAccountForm(happyforms.ModelForm):
    class Meta:
        model = ExternalAccount
        fields = ['type', 'identifier', 'privacy']

    def clean(self):
        cleaned_data = super(ExternalAccountForm, self).clean()
        identifier = cleaned_data.get('identifier')
        type = cleaned_data.get('type')

        if type:
            validator = ExternalAccount.ACCOUNT_TYPES[type].get('validator')
            if validator:
                cleaned_data['identifier'] = validator(identifier)
        return cleaned_data

AccountsFormset = inlineformset_factory(UserProfile, ExternalAccount,
                                        form=ExternalAccountForm, extra=1)


class SearchForm(happyforms.Form):
    q = forms.CharField(required=False)
    limit = forms.IntegerField(
        widget=forms.HiddenInput, required=False, min_value=1,
        max_value=settings.ITEMS_PER_PAGE)
    include_non_vouched = forms.BooleanField(
        label=_lazy(u'Include non-vouched'), required=False)

    def clean_limit(self):
        limit = self.cleaned_data['limit'] or settings.ITEMS_PER_PAGE
        return limit


class UserForm(happyforms.ModelForm):
    """Instead of just inhereting form a UserProfile model form, this
    base class allows us to also abstract over methods that have to do
    with the User object that need to exist in both Registration and
    Profile.

    """
    username = forms.CharField(label=_lazy(u'Username'))

    class Meta:
        model = User
        fields = ['username']

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


class ProfileForm(happyforms.ModelForm):
    photo = forms.ImageField(label=_lazy(u'Profile Photo'), required=False)
    photo_delete = forms.BooleanField(label=_lazy(u'Remove Profile Photo'),
                                      required=False)
    date_mozillian = forms.DateField(
        required=False,
        label=_lazy(u'When did you get involved with Mozilla?'),
        widget=MonthYearWidget(years=range(1998, datetime.today().year + 1),
                               required=False))
    languages = forms.CharField(
        label=_lazy(u'Start typing to add a language you speak (example: '
                    'English, French, German)'), required=False)
    skills = forms.CharField(
        label=_lazy(u'Start typing to add a skill (example: Python, '
                    'javascript, Graphic Design, User Research)'),
        required=False)

    class Meta:
        model = UserProfile
        fields = ('full_name', 'ircname', 'bio', 'photo', 'country',
                  'region', 'city', 'allows_community_sites', 'tshirt',
                  'title', 'allows_mozilla_sites',
                  'date_mozillian', 'timezone',
                  'privacy_photo', 'privacy_full_name', 'privacy_ircname',
                  'privacy_email', 'privacy_timezone', 'privacy_tshirt',
                  'privacy_bio', 'privacy_city', 'privacy_region',
                  'privacy_country', 'privacy_groups',
                  'privacy_skills', 'privacy_languages',
                  'privacy_date_mozillian', 'privacy_title')
        widgets = {'bio': forms.Textarea()}

    def __init__(self, *args, **kwargs):
        locale = kwargs.pop('locale', 'en-US')

        super(ProfileForm, self).__init__(*args, **kwargs)
        country_list = product_details.get_regions(locale).items()
        country_list = sorted(country_list, key=lambda country: country[1])
        country_list.insert(0, ('', '----'))
        self.fields['country'].choices = country_list

    def clean_photo(self):
        """Clean possible bad Image data.

        Try to load EXIF data from image. If that fails, remove EXIF
        data by re-saving the image. Related bug 919736.

        """
        photo = self.cleaned_data['photo']
        if photo and isinstance(photo, UploadedFile):
            image = Image.open(photo.file)
            try:
                image._get_exif()
            except (AttributeError, IOError, KeyError, IndexError):
                cleaned_photo = StringIO()
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                image.save(cleaned_photo, format='JPEG', quality=95)
                photo.file = cleaned_photo
                photo.size = cleaned_photo.tell()
        return photo

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

    def clean_skills(self):
        if not re.match(r'^[a-zA-Z0-9 .:,-]*$', self.cleaned_data['skills']):
            raise forms.ValidationError(_(u'Skills can only contain '
                                           'alphanumeric characters, dashes, '
                                           'spaces.'))
        skills = self.cleaned_data['skills']
        return filter(lambda x: x,
                      map(lambda x: x.strip() or False,
                          skills.lower().split(',')))

    def save(self):
        """Save the data to profile."""
        self.instance.set_membership(Skill, self.cleaned_data['skills'])
        self.instance.set_membership(Language, self.cleaned_data['languages'])
        super(ProfileForm, self).save()


class EmailForm(happyforms.Form):
    email = forms.EmailField(label=_lazy(u'Email'))

    def clean_email(self):
        email = self.cleaned_data['email']
        if (User.objects
            .exclude(pk=self.initial['user_id']).filter(email=email).exists()):
            raise forms.ValidationError(_('Email is currently associated with another user.'))
        return email

    def email_changed(self):
        return self.cleaned_data['email'] != self.initial['email']


class RegisterForm(ProfileForm):
    optin = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': 'checkbox'}),
        required=True)


class VouchForm(happyforms.Form):
    """Vouching is captured via a user's id."""
    vouchee = forms.IntegerField(widget=forms.HiddenInput)


class InviteForm(happyforms.ModelForm):

    def clean_recipient(self):
        recipient = self.cleaned_data['recipient']
        if User.objects.filter(email=recipient,
                               userprofile__is_vouched=True).exists():
            raise forms.ValidationError(
                _(u'You cannot invite someone who has already been vouched.'))
        return recipient

    class Meta:
        model = Invite
        fields = ['recipient', 'message']
