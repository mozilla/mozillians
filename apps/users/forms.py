from django import forms

from tower import ugettext_lazy as _lazy

from users.models import UserProfile
from phonebook.forms import UserForm


class RegistrationForm(UserForm):
    optin = forms.BooleanField(
            widget=forms.CheckboxInput(attrs={'class': 'checkbox'}),
            required=True)

    class Meta:
        model = UserProfile
        fields = ('bio',)
        widgets = {
            'bio': forms.Textarea(),
        }
