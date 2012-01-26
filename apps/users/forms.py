from django import forms

from tower import ugettext_lazy as _lazy

from phonebook.forms import ProfileForm


class RegistrationForm(ProfileForm):
    code = forms.CharField(widget=forms.HiddenInput, required=False)

    optin = forms.BooleanField(
            label=_lazy(u"I'm okay with you handling this info as you "
                        u'explain in your privacy policy.'),
            widget=forms.CheckboxInput(attrs={'class': 'checkbox'}))

    def clean(self):
        super(RegistrationForm, self).clean()

        data = self.cleaned_data

        return data


