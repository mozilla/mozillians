from django import forms

from tower import ugettext_lazy as _lazy

from users.models import UserProfile
from phonebook.forms import UserForm


class RegistrationForm(UserForm):
    username = forms.CharField(
                label=_lazy(u'Username'), max_length=30, required=False,
                widget=forms.TextInput(attrs={'placeholder': 'Example: IRC Nickname'}))

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

    def save(self, user):
        d = self.cleaned_data
        if 'username' in d:
            d['ircname'] = d['username']
        super(RegistrationForm, self).save(user)
