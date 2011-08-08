from django import forms

from django.forms.util import ErrorList

from tower import ugettext_lazy as _lazy


class AuthenticationForm(forms.Form):
    username = forms.CharField(required=True)

    password = forms.CharField(max_length=255, required=True)


class RegistrationForm(forms.Form):
    email = forms.EmailField(label=_lazy(u'Primary Email'), required=True)
    password = forms.CharField(min_length=8, max_length=255,
                               label=_lazy(u'Password'), required=True,
                               widget=forms.PasswordInput(render_value=False))
    confirmp = forms.CharField(label=_lazy(u'Confirm Password'),
                               widget=forms.PasswordInput(render_value=False),
                               required=True)

    first_name = forms.CharField(label=_lazy(u'First Name'), required=False)
    last_name = forms.CharField(label=_lazy(u'Last Name'), required=True)

    #recaptcha = captcha.fields.ReCaptchaField()
    optin = forms.BooleanField(
            label=_lazy(u'I will bow before Zuul''s might.'),
            widget=forms.CheckboxInput(
            attrs=dict(css_class='checkbox')))

    def clean(self):
        super(RegistrationForm, self).clean()

        data = self.cleaned_data

        # Passwords
        p1 = data.get('password')
        p2 = data.get('confirmp')

        if p1 != p2:
            msg = _lazy(u'The passwords did not match.')
            self._errors['confirmp'] = ErrorList([msg])
            if p2:
                del data['confirmp']

        return data
