from django import forms

from tower import ugettext_lazy as _lazy

from users.models import UserProfile


class RegistrationForm(forms.ModelForm):
    first_name = forms.CharField(label=_lazy(u'First Name'), max_length=30,
                                                             required=False)
    last_name = forms.CharField(label=_lazy(u'Last Name'), max_length=30,
                                                           required=True)

    optin = forms.BooleanField(
            label=_lazy(u"I'm okay with you handling this info as you "
                        u'explain in your privacy policy.'),
            widget=forms.CheckboxInput(attrs={'class': 'checkbox'}),
            required=True)

    class Meta:
        model = UserProfile
        fields = ('bio',)
        widgets = {
            'bio': forms.Textarea(),
        }

    def save(self, user):
        d = self.cleaned_data
        user.first_name = d['first_name']
        user.last_name = d['last_name']
        user.save()
        super(forms.ModelForm, self).save()
