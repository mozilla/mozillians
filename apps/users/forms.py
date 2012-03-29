from django import forms

from tower import ugettext_lazy as _lazy

from users.models import UserProfile
from phonebook.forms import UserForm


class RegistrationForm(UserForm):
    optin = forms.BooleanField(
            label=_lazy(u"I'm okay with you handling this info as you "
                        u'explain in your privacy policy.'),
            widget=forms.CheckboxInput(attrs={'class': 'checkbox'}),
            required=True)

    class Meta:
        model = UserProfile
        fields = ('first_name', 'last_name', 'username', 'bio', 'optin')
        widgets = {
            'bio': forms.Textarea(),
        }
