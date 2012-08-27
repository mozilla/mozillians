import re

from django import forms
from django.forms.fields import MultipleChoiceField
from django.forms.widgets import CheckboxSelectMultiple

from tower import ugettext as _, ugettext_lazy as _lazy

from users.models import UserProfile
from phonebook.forms import UserForm

from groups.models import Group, Skill, Language
from groups.helpers import stringify_groups


class RegistrationForm(UserForm):
    username = forms.CharField(
                label=_lazy(u'Username'), max_length=30, required=False,
                widget=forms.TextInput(attrs={'placeholder': 'Example: IRC Nickname'}))

    groups = forms.ModelMultipleChoiceField(widget=forms.CheckboxSelectMultiple, label=_lazy(
             u'Do you know which functional areas you would like to help or already helping? '
             'Choose from the ones below to get started.'), queryset=Group.get_curated(),
             required=False)
    skills = forms.CharField(label=_lazy(
             u'Enter your skills (e.g. Python, Photoshop'
             ') below:'), required=False)
    languages = forms.CharField(label=_lazy(
                u'Mozillians speak many languages (e.g. English, French). Find and be '
                'found by others who speak the same languages as you.'), required=False)


    optin = forms.BooleanField(
            label=_lazy(u"I'm okay with you handling this info as you "
                        u'explain in your privacy policy.'),
            widget=forms.CheckboxInput(attrs={'class': 'checkbox'}),
            required=True)

    class Meta:
        model = UserProfile
        fields = ('ircname', 'website', 'bio', 'photo', 'country', 'region',
                  'city')
        widgets = {
            'bio': forms.Textarea()
        }

    def clean_skills(self):
        if not re.match(r'^[a-zA-Z0-9 .:,-]*$', self.cleaned_data['skills']):
            raise forms.ValidationError(_(u'Skills can only contain '
                                           'alphanumeric characters, dashes, '
                                           'spaces.'))
        return [s.strip()
                for s in self.cleaned_data['skills'].lower().split(',')
                if s and ',' not in s]

    def clean_languages(self):
        if not re.match(r'^[a-zA-Z0-9 .:,-]*$', self.cleaned_data['languages']):
            raise forms.ValidationError(_(u'Languages can only contain '
                                           'alphanumeric characters, dashes, '
                                           'spaces.'))
        return [s.strip()
                for s in self.cleaned_data['languages'].lower().split(',')
                if s and ',' not in s]

    def clean(self):
        """Make sure geographic fields aren't underspecified."""
        cleaned_data = super(RegistrationForm, self).clean()
        # Rather than raising ValidationErrors for the whole form, we can
        # add errors to specific fields.
        if cleaned_data['city'] and not cleaned_data['region']:
            self._errors['region'] = [_(u'You must specify a region to '
                                         'specify a city.')]
        if cleaned_data['region'] and not cleaned_data['country']:
            self._errors['country'] = [_(u'You must specify a country to '
                                         'specify a district.')]
        return cleaned_data

    def save(self, user):
        d = self.cleaned_data
        if 'username' in d:
            d['ircname'] = d['username']
        self.instance.set_membership(Skill, self.cleaned_data['skills'])
        self.instance.set_membership(Language, self.cleaned_data['languages'])
        super(RegistrationForm, self).save(user)
