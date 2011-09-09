from django import forms
from django.forms.util import ErrorList
from django.template import loader
from django.utils.http import int_to_base36
from django.contrib import auth
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.models import get_current_site

import commonware.log
from tower import ugettext_lazy as _lazy


import larper

log = commonware.log.getLogger('m.users')


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
    code = forms.CharField(widget=forms.HiddenInput, required=False)

    #recaptcha = captcha.fields.ReCaptchaField()
    optin = forms.BooleanField(
            label=_lazy(u"I'm okay with you handling this info as you "
                        u'explain in your privacy policy.'),
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


class PasswordChangeForm(auth.forms.PasswordChangeForm):
    """Do LDAP goodness instead of RDBMS goodness."""

    def clean_old_password(self):
        """
        Do a bind with email and old_password to make sure old
        credentials are valid.
        """
        password = self.cleaned_data.get('old_password')
        user = auth.authenticate(username=self.user.username, 
                                 password=password)

        if user:
            log.debug("Old Password is good")
            return password
        else:
            log.info("Auth with old password failed.")
            msg = _lazy("Your old password was entered incorrectly. "
                        "Please enter it again.")
            raise forms.ValidationError(msg)

    def save(self):
        password = self.cleaned_data.get('new_password1')
        rv = larper.change_password(self.user.unique_id,
                                    self.cleaned_data.get('old_password'),
                                    password)
        if rv:
            return self.user
        else:
            log.error("Unable to change password for %s" % self.user.unique_id)
            raise Exception("Unknown error changing password")


class PasswordResetForm(auth.forms.PasswordResetForm):
    def clean_email(self):
        """
        Validates that an active user exists with the given email address.
        """
        email = self.cleaned_data["email"]
        self.users_cache = auth.models.User.objects.filter(email__iexact=email)
        # NOTICE: If we ever drop django-auth-ldap, this Form will break.
        if not len(self.users_cache):
            msg = _lazy("That e-mail address doesn't have an associated "
                        "user account. Are you sure you've registered?")
            raise forms.ValidationError(msg)
        return email

    def save(self, domain_override=None,
             subject_template_name='registration/password_reset_subject.txt',
             email_template_name='registration/password_reset_email.html',
             use_https=False, token_generator=default_token_generator,
             from_email=None, request=None):
        """
        Generates a one-use only link for resetting password
        and sends to the user.
        """
        from django.core.mail import send_mail
        for user in self.users_cache:
            if not domain_override:
                current_site = get_current_site(request)
                site_name = current_site.name
                domain = current_site.domain
            else:
                site_name = domain = domain_override
            c = {
                'email': user.email,
                'domain': domain,
                'site_name': site_name,
                'uid': int_to_base36(user.id),
                'user': user,
                'token': token_generator.make_token(user),
                'protocol': use_https and 'https' or 'http',
            }
            subject = loader.render_to_string(subject_template_name, c)
            # Email subject *must not* contain newlines
            subject = ''.join(subject.splitlines())
            email = loader.render_to_string(email_template_name, c)
            send_mail(subject, email, from_email, [user.email])


class SetPasswordForm(auth.forms.SetPasswordForm):
    def save(self, commit=True):
        larper.set_password(self.user.username,
                            self.cleaned_data['new_password1'])
        return self.user
