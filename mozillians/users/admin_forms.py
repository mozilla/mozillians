from django import forms
from django.contrib.auth.models import User
from django.forms import ValidationError

from dal import autocomplete

from mozillians.users.models import AbuseReport, ExternalAccount, UserProfile, Vouch


class VouchAutocompleteForm(forms.ModelForm):

    class Meta:
        model = Vouch
        fields = '__all__'
        widgets = {
            'vouchee': autocomplete.ModelSelect2(url='users:vouchee-autocomplete'),
            'voucher': autocomplete.ModelSelect2(url='users:voucher-autocomplete')
        }


class AbuseReportAutocompleteForm(forms.ModelForm):

    class Meta:
        model = AbuseReport
        fields = '__all__'
        widgets = {
            'profile': autocomplete.ModelSelect2(url='users:vouchee-autocomplete'),
            'reporter': autocomplete.ModelSelect2(url='users:vouchee-autocomplete'),
        }


class AlternateEmailForm(forms.ModelForm):
    def save(self, *args, **kwargs):
        self.instance.type = ExternalAccount.TYPE_EMAIL
        return super(AlternateEmailForm, self).save(*args, **kwargs)

    class Meta:
        model = ExternalAccount
        exclude = ['type']


class UserProfileAdminForm(forms.ModelForm):
    username = forms.CharField()
    email = forms.CharField()
    last_login = forms.DateTimeField(required=False)
    date_joined = forms.DateTimeField(required=False)

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.get('instance')
        if self.instance:
            self.base_fields['username'].initial = self.instance.user.username
            self.base_fields['email'].initial = self.instance.user.email
        super(UserProfileAdminForm, self).__init__(*args, **kwargs)

    def clean_username(self):
        username = self.cleaned_data['username']
        if (User.objects.exclude(pk=self.instance.user.pk)
                .filter(username=username).exists()):
            raise ValidationError('Username already exists')
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if (User.objects.exclude(pk=self.instance.user.pk)
                .filter(email=email).exists()):
            raise ValidationError('Email already exists')
        return email

    def save(self, *args, **kwargs):
        if self.instance:
            self.instance.user.username = self.cleaned_data.get('username')
            self.instance.user.email = self.cleaned_data.get('email')
            self.instance.user.save()
        return super(UserProfileAdminForm, self).save(*args, **kwargs)

    class Meta:
        model = UserProfile
        fields = '__all__'
