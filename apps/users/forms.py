from django import forms

from tower import ugettext_lazy as _lazy

from users.models import UserProfile
from phonebook.forms import ProfileForm


class RegistrationForm(ProfileForm):
    optin = forms.BooleanField(
            label=_lazy(u"I'm okay with you handling this info as you "
                        u"explain in Mozilla's privacy policy."),
            widget=forms.CheckboxInput(attrs={'class': 'checkbox'}),
            required=True)

    class Meta:
        # Model form stuff
        model = UserProfile
        fields = ('ircname', 'website', 'bio', 'photo', 'country', 'region',
                  'city')
        exclude = ('display_name', 'groups')
        widgets = {'bio': forms.Textarea()}
