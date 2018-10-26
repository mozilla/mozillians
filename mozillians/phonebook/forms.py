import re
from cStringIO import StringIO
from datetime import datetime

from django import forms
from django.contrib.auth.models import User
from django.core.files.uploadedfile import UploadedFile
from django.forms.models import BaseInlineFormSet, inlineformset_factory
from django.forms.widgets import RadioSelect
from django.utils.translation import ugettext as _, ugettext_lazy as _lazy

import django_filters
import happyforms
from dal import autocomplete
from haystack.forms import ModelSearchForm as HaystackSearchForm
from haystack.query import SQ, SearchQuerySet
from nocaptcha_recaptcha.fields import NoReCaptchaField
from pytz import common_timezones
from PIL import Image

from mozillians.api.models import APIv2App
from mozillians.common.urlresolvers import reverse
from mozillians.groups.models import Group
from mozillians.phonebook.models import Invite
from mozillians.phonebook.validators import validate_username
from mozillians.phonebook.widgets import MonthYearWidget
from mozillians.users import get_languages_for_locale
from mozillians.users.managers import PUBLIC
from mozillians.users.models import AbuseReport, ExternalAccount, IdpProfile, Language, UserProfile
from mozillians.users.search_indexes import IdpProfileIndex, UserProfileIndex


REGEX_NUMERIC = re.compile(r'\d+', re.IGNORECASE)


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


class IdpProfileForm(happyforms.ModelForm):
    """Form for the IdpProfile model."""

    class Meta:
        model = IdpProfile
        fields = ['privacy']


IdpProfileFormset = inlineformset_factory(UserProfile, IdpProfile,
                                          form=IdpProfileForm, extra=0)


class EmailPrivacyForm(happyforms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['privacy_email']


def filter_vouched(qs, choice):
    if choice == SearchFilter.CHOICE_ONLY_VOUCHED:
        return qs.filter(is_vouched=True)
    elif choice == SearchFilter.CHOICE_ONLY_UNVOUCHED:
        return qs.filter(is_vouched=False)
    return qs


class SearchFilter(django_filters.FilterSet):
    CHOICE_ONLY_VOUCHED = 'yes'
    CHOICE_ONLY_UNVOUCHED = 'no'
    CHOICE_ALL = 'all'

    CHOICES = (
        (CHOICE_ONLY_VOUCHED, _lazy('Vouched')),
        (CHOICE_ONLY_UNVOUCHED, _lazy('Unvouched')),
        (CHOICE_ALL, _lazy('All')),
    )

    vouched = django_filters.ChoiceFilter(
        name='vouched', label=_lazy(u'Display only'), required=False,
        choices=CHOICES, action=filter_vouched)

    class Meta:
        model = UserProfile
        fields = ['vouched', 'skills', 'groups', 'timezone']

    def __init__(self, *args, **kwargs):
        super(SearchFilter, self).__init__(*args, **kwargs)
        self.filters['timezone'].field.choices.insert(0, ('', _lazy(u'All timezones')))


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


class BasicInformationForm(happyforms.ModelForm):
    photo = forms.ImageField(label=_lazy(u'Profile Photo'), required=False)
    photo_delete = forms.BooleanField(label=_lazy(u'Remove Profile Photo'),
                                      required=False)

    class Meta:
        model = UserProfile
        fields = ('photo', 'privacy_photo', 'full_name', 'privacy_full_name',
                  'full_name_local', 'privacy_full_name_local', 'bio', 'privacy_bio',)
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


class SkillsForm(happyforms.ModelForm):

    def __init__(self, *args, **kwargs):
        """Override init method."""
        super(SkillsForm, self).__init__(*args, **kwargs)
        # Override the url to pass along the locale.
        # This is needed in order to post to the correct url through ajax
        self.fields['skills'].widget.url = reverse('groups:skills-autocomplete')

    class Meta:
        model = UserProfile
        fields = ('privacy_skills', 'skills',)
        widgets = {
            'skills': autocomplete.ModelSelect2Multiple(
                url='groups:skills-autocomplete',
                attrs={
                    'data-placeholder': (u'Start typing to add a skill (example: Python, '
                                         u'javascript, Graphic Design, User Research)'),
                    'data-minimum-input-length': 2
                }
            )
        }


class LanguagesPrivacyForm(happyforms.ModelForm):

    class Meta:
        model = UserProfile
        fields = ('privacy_languages',)


def get_timezones_list():
    return common_timezones


class LocationForm(happyforms.ModelForm):
    """Form to provide location data."""

    timezone = autocomplete.Select2ListChoiceField(
        choice_list=get_timezones_list,
        required=False,
        widget=autocomplete.ListSelect2(url='users:timezone-autocomplete',
                                        forward=['country', 'city', 'region']))

    def __init__(self, *args, **kwargs):
        """Override init method.

        Make country a required field.
        """
        super(LocationForm, self).__init__(*args, **kwargs)
        self.fields['country'].required = True
        if self.data and (self.data.get('city') or self.data.get('country')):
            self.fields['country'].required = False

    def clean(self):
        """Override clean method.

        We need at least the country of the user.
        If a user supplies a city or a region, we can extract
        the data from there.
        """
        super(LocationForm, self).clean()

        country = self.cleaned_data.get('country')
        region = self.cleaned_data.get('region')
        city = self.cleaned_data.get('city')

        if not city and not country and not region:
            msg = _(u'Please supply your location data.')
            raise forms.ValidationError(msg)

        if region:
            self.cleaned_data['country'] = region.country

        if city:
            self.cleaned_data['country'] = city.country
            self.cleaned_data['region'] = city.region

        return self.cleaned_data

    class Meta:
        model = UserProfile
        fields = ('timezone', 'privacy_timezone', 'city', 'privacy_city', 'region',
                  'privacy_region', 'country', 'privacy_country',)
        widgets = {
            'country': autocomplete.ModelSelect2(
                url='users:country-autocomplete',
                attrs={
                    'data-placeholder': u'Start typing to select a country.',
                    'data-minimum-input-length': 2
                }
            ),
            'region': autocomplete.ModelSelect2(
                url='users:region-autocomplete',
                forward=['country'],
                attrs={
                    'data-placeholder': u'Start typing to select a region.',
                    'data-minimum-input-length': 3
                }
            ),
            'city': autocomplete.ModelSelect2(
                url='users:city-autocomplete',
                forward=['country', 'region'],
                attrs={
                    'data-placeholder': u'Start typing to select a city.',
                    'data-minimum-input-length': 3
                }
            )
        }


class ContributionForm(happyforms.ModelForm):
    date_mozillian = forms.DateField(
        required=False,
        label=_lazy(u'When did you get involved with Mozilla?'),
        widget=MonthYearWidget(years=range(1998, datetime.today().year + 1),
                               required=False))

    class Meta:
        model = UserProfile
        fields = ('title', 'privacy_title', 'date_mozillian', 'privacy_date_mozillian',
                  'story_link', 'privacy_story_link',)


class TshirtForm(happyforms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('tshirt', 'privacy_tshirt',)


class GroupsPrivacyForm(happyforms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('privacy_groups',)


class IRCForm(happyforms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('ircname', 'privacy_ircname',)


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
                                         extra=1,
                                         fields='__all__')


class EmailForm(happyforms.Form):
    email = forms.EmailField(label=_lazy(u'Email'))

    def clean_email(self):
        email = self.cleaned_data['email']
        if (User.objects.exclude(pk=self.initial['user_id']).filter(email=email).exists()):
            raise forms.ValidationError(_(u'Email is currently associated with another user.'))
        return email

    def email_changed(self):
        return self.cleaned_data['email'] != self.initial['email']


class RegisterForm(BasicInformationForm, LocationForm):
    optin = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': 'checkbox'}),
        required=True)
    captcha = NoReCaptchaField()

    class Meta:
        model = UserProfile
        fields = ('photo', 'full_name', 'timezone', 'privacy_photo', 'privacy_full_name', 'optin',
                  'privacy_timezone', 'privacy_city', 'privacy_region', 'privacy_country',
                  'country', 'region', 'city',)
        widgets = {
            'country': autocomplete.ModelSelect2(
                url='users:country-autocomplete',
                attrs={
                    'data-placeholder': u'Start typing to select a country.',
                    'data-minimum-input-length': 2
                }
            ),
            'region': autocomplete.ModelSelect2(
                url='users:region-autocomplete',
                forward=['country'],
                attrs={
                    'data-placeholder': u'Start typing to select a region.',
                    'data-minimum-input-length': 3
                }
            ),
            'city': autocomplete.ModelSelect2(
                url='users:city-autocomplete',
                forward=['country', 'region'],
                attrs={
                    'data-placeholder': u'Start typing to select a city.',
                    'data-minimum-input-length': 3
                }
            )
        }


class VouchForm(happyforms.Form):
    """Vouching is captured via a user's id and a description of the reason for vouching."""
    description = forms.CharField(
        label=_lazy(u'Provide a reason for vouching with relevant links'),
        widget=forms.Textarea(attrs={'rows': 10, 'cols': 20, 'maxlength': 500}),
        max_length=500,
        error_messages={'required': _(u'You must enter a reason for vouching for this person.')}
    )


class InviteForm(happyforms.ModelForm):
    message = forms.CharField(
        label=_lazy(u'Personal message to be included in the invite email'),
        required=False, widget=forms.Textarea(),
    )
    recipient = forms.EmailField(label=_lazy(u"Recipient's email"))

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


class APIKeyRequestForm(happyforms.ModelForm):

    class Meta:
        model = APIv2App
        fields = ('name', 'description', 'url',)


class AbuseReportForm(happyforms.ModelForm):

    class Meta:
        model = AbuseReport
        fields = ('type',)
        widgets = {
            'type': RadioSelect
        }
        labels = {
            'type': _(u'What would you like to report?')
        }


class PhonebookSearchForm(HaystackSearchForm):
    """Django Haystack's search form."""

    def __init__(self, *args, **kwargs):
        """Initialize search form.

        Get the user object passed from the CBV.
        """
        self.request = kwargs.pop('request', None)
        self.country = kwargs.pop('country', '')
        self.region = kwargs.pop('region', '')
        self.city = kwargs.pop('city', '')
        super(PhonebookSearchForm, self).__init__(*args, **kwargs)

    def clean(self, *args, **kwargs):
        cdata = super(PhonebookSearchForm, self).clean(*args, **kwargs)
        if not (self.country or self.city or self.region) and not cdata.get('q', '').strip():
            self.errors['q'] = self.error_class([u'This field is required.'])
        if ('users.userprofile' in cdata['models']
            or 'users.idpprofile' in cdata['models']
                or not cdata['models']):
            cdata['is_profile_query'] = True
        if ('groups.group' in cdata['models'] or not cdata['models'] and not
                self.request.user.is_anonymous()):
            cdata['is_group_query'] = True
        return cdata

    def search(self):
        """Search on the ES index the query sting provided by the user."""

        search_term = self.cleaned_data.get('q')
        profile = None
        location_query = {}

        if self.country:
            location_query['country'] = self.country
            location_query['privacy_country__gte'] = None
        if self.region:
            location_query['region'] = self.region
            location_query['privacy_region__gte'] = None
        if self.city:
            location_query['city'] = self.city
            location_query['privacy_city__gte'] = None

        try:
            profile = self.request.user.userprofile
        except AttributeError:
            # This is an AnonymousUser
            privacy_level = PUBLIC
        else:
            privacy_level = profile.privacy_level

        if profile and profile.is_vouched:
            # If this is empty, it will default to all models.
            search_models = self.get_models()
        else:
            # Anonymous and un-vouched users cannot search groups
            search_models = [UserProfile, IdpProfile]

        if location_query:
            for k in location_query.keys():
                if k.startswith('privacy_'):
                    location_query[k] = privacy_level
            return SearchQuerySet().filter(**location_query).load_all() or self.no_query_found()

        # Calling super will handle with form validation and
        # will also search in fields that are not explicit queried through `text`
        sqs = super(PhonebookSearchForm, self).search().models(*search_models)

        if not sqs:
            return self.no_query_found()

        query = SQ()
        q_args = {}
        # Profiles Search
        all_indexed_fields = UserProfileIndex.fields.keys() + IdpProfileIndex.fields.keys()
        privacy_indexed_fields = [field for field in all_indexed_fields
                                  if field.startswith('privacy_')]
        # Every profile object in mozillians.org has privacy settings.
        # Let's take advantage of this and compare the indexed fields
        # with the ones listed in a profile in order to build the query to ES.
        for p_field in privacy_indexed_fields:
            # this is the field that we are going to query
            q_field = p_field.split('_', 1)[1]
            # The user needs to have less or equal permission number with the queried field
            # (lower number, means greater permission level)
            q_args = {
                q_field: search_term,
                '{0}__gte'.format(p_field): privacy_level
            }
            query.add(SQ(**q_args), SQ.OR)

        # Username is always public
        query.add(SQ(**{'username': search_term}), SQ.OR)

        # Group Search
        if not search_models or Group in search_models:
            # Filter only visible groups.
            query.add(SQ(**{'visible': True}), SQ.OR)

        return sqs.filter(query).load_all()
