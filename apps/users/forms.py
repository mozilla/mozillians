from django import forms

from django.forms.util import ErrorList

from tower import ugettext as _


class AuthenticationForm(forms.Form):
    username = forms.CharField(required=True)

    password = forms.CharField(max_length=255, required=True)


class RegistrationForm(forms.Form):
    username = forms.EmailField(label=_('Primary Email'), required=True)
    password = forms.CharField(min_length=8, max_length=255,
                               label=_('Password'), required=True,
                               widget=forms.PasswordInput(render_value=False))
    confirmp = forms.CharField(label=_('Confirm Password'),
                               widget=forms.PasswordInput(render_value=False),
                               required=True)

    first_name = forms.CharField(label=_('First Name'), required=False)
    last_name = forms.CharField(label=_('Last Name'), required=True)

    #recaptcha = captcha.fields.ReCaptchaField()
    optin = forms.BooleanField(label=_('I will bow before Zuul''s might.'),
                               widget=forms.CheckboxInput(
                                   attrs=dict(css_class='checkbox')))

    def clean(self):
        super(RegistrationForm, self).clean()

        data = self.cleaned_data

        # Passwords
        p1 = data.get('password')
        p2 = data.get('confirmp')

        if p1 != p2:
            msg = _('The passwords did not match.')
            self._errors['confirmp'] = ErrorList([msg])
            if p2:
                del data['confirmp']

        return data
