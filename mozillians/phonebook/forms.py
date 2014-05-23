import re
from cStringIO import StringIO
from datetime import datetime

from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.forms.models import BaseInlineFormSet, inlineformset_factory

import happyforms
from PIL import Image
from tower import ugettext as _, ugettext_lazy as _lazy

from mozillians.groups.models import Skill
from mozillians.phonebook.models import Invite
from mozillians.phonebook.validators import validate_username
from mozillians.phonebook.widgets import MonthYearWidget
from mozillians.users import get_languages_for_locale
from mozillians.users.models import ExternalAccount, Language, UserProfile


REGEX_NUMERIC = re.compile('\d+', re.IGNORECASE)


class ExternalAccountForm(happyforms.ModelForm):
    class Meta:
        model = ExternalAccount
        fields = ['type', 'identifier', 'privacy']

    def clean(self):
        cleaned_data = super(ExternalAccountForm, self).clean()
        identifier = cleaned_data.get('identifier')
        account_type = cleaned_data.get('type')

        if account_type and identifier:
            # If the Account expects an identifier and user provided a
            # full URL, try to extract the identifier from the URL.
            url = ExternalAccount.ACCOUNT_TYPES[account_type].get('url')
            if url and identifier.startswith('http'):
                url_pattern_re = url.replace('{identifier}', '(.+)')
                identifier = identifier.rstrip('/')
                url_pattern_re = url_pattern_re.rstrip('/')
                match = re.match(url_pattern_re, identifier)
                if match:
                    identifier = match.groups()[0]

            validator = ExternalAccount.ACCOUNT_TYPES[account_type].get('validator')
            if validator:
                identifier = validator(identifier)

            cleaned_data['identifier'] = identifier

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
            raise forms.ValidationError(_(u'This username is in use. Please try'
                                          u' another.'))

        # No funky characters in username.
        if not re.match(r'^[\w.@+-]+$', username):
            raise forms.ValidationError(_(u'Please use only alphanumeric'
                                          u' characters'))

        if not validate_username(username):
            raise forms.ValidationError(_(u'This username is not allowed, '
                                          u'please choose another.'))
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
    skills = forms.CharField(
        label='',
        help_text=_lazy(u'Start typing to add a skill (example: Python, '
                        u'javascript, Graphic Design, User Research)'),
        required=False)

    class Meta:
        model = UserProfile
        fields = ('full_name', 'ircname', 'bio', 'photo',
                  'allows_community_sites', 'tshirt',
                  'title', 'allows_mozilla_sites',
                  'date_mozillian', 'story_link', 'timezone',
                  'lat', 'lng',
                  'privacy_photo', 'privacy_full_name', 'privacy_ircname',
                  'privacy_email', 'privacy_timezone', 'privacy_tshirt',
                  'privacy_bio', 'privacy_geo_city', 'privacy_geo_region',
                  'privacy_geo_country', 'privacy_groups',
                  'privacy_skills', 'privacy_languages',
                  'privacy_date_mozillian', 'privacy_story_link', 'privacy_title')
        widgets = {'bio': forms.Textarea()}

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

    def clean_skills(self):
        if not re.match(r'^[a-zA-Z0-9 +.:,-]*$', self.cleaned_data['skills']):
            # Commas cannot be included in skill names because we use them to
            # separate names in a list
            raise forms.ValidationError(_(u'Skills can only contain '
                                          u'alphanumeric characters '
                                          u'and +.:-.'))
        skills = self.cleaned_data['skills']
        return filter(lambda x: x,
                      map(lambda x: x.strip() or False,
                          skills.lower().split(',')))

    def clean(self):
        # If long/lat were provided, make sure they point at a country somewhere...
        if self.cleaned_data.get('lat') is not None and self.cleaned_data.get('lng') is not None:
            self.instance.lat = self.cleaned_data['lat']
            self.instance.lng = self.cleaned_data['lng']
            self.instance.reverse_geocode()
            if not self.instance.geo_country:
                raise ValidationError(_("Location must be inside a country."))
        return self.cleaned_data

    def save(self, *args, **kwargs):
        """Save the data to profile."""
        self.instance.set_membership(Skill, self.cleaned_data['skills'])
        super(ProfileForm, self).save(*args, **kwargs)


class BaseLanguageFormSet(BaseInlineFormSet):

    def __init__(self, *args, **kwargs):
        self.locale = kwargs.pop('locale', 'en')
        super(BaseLanguageFormSet, self).__init__(*args, **kwargs)

    def add_fields(self, form, index):
        super(BaseLanguageFormSet, self).add_fields(form, index)
        choices = [('', '---------')] + get_languages_for_locale(self.locale)
        form.fields['code'].choices = choices

    class Meta:
        models = Language
        fields = ['code']


LanguagesFormset = inlineformset_factory(UserProfile, Language,
                                         formset=BaseLanguageFormSet,
                                         extra=1)


class EmailForm(happyforms.Form):
    email = forms.EmailField(label=_lazy(u'Email'))

    def clean_email(self):
        email = self.cleaned_data['email']
        if (User.objects
            .exclude(pk=self.initial['user_id']).filter(email=email).exists()):
            raise forms.ValidationError(_(u'Email is currently associated with another user.'))
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
    message = forms.CharField(label=_lazy('Message'), required=False, widget=forms.Textarea())

    def clean_recipient(self):
        recipient = self.cleaned_data['recipient']
        if User.objects.filter(email=recipient,
                               userprofile__is_vouched=True).exists():
            raise forms.ValidationError(
                _(u'You cannot invite someone who has already been vouched.'))
        return recipient

    class Meta:
        model = Invite
        fields = ['recipient']
