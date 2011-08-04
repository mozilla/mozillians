from django import forms

from tower import ugettext_lazy as _lazy, ugettext as _


class SearchForm(forms.Form):
    q = forms.CharField(widget=forms.HiddenInput, required=True)


class ProfileForm(forms.Form):
    first_name = forms.CharField(label=_('First Name'), required=False)
    last_name = forms.CharField(label=_('Last Name'), required=True)
    biography = forms.CharField(label=_('Bio'),
                                widget=forms.Textarea(),
                                required=False)
    photo = forms.ImageField(label=_('Profile Photo'), required=False)

    # Remote System Ids
    # Tightly coupled with larper.UserSession.form_to_service_ids_attrs
    irc_nickname = forms.CharField(label=_('IRC Nickname'), required=False)
    irc_nickname_unique_id = forms.CharField(widget=forms.HiddenInput,
                                             required=False)


class DeleteForm(forms.Form):
    unique_id = forms.CharField(widget=forms.HiddenInput)


class VouchForm(forms.Form):
    """ Vouching is captured via a user's unique_id """
    voucher = forms.CharField(widget=forms.HiddenInput)
    vouchee = forms.CharField(widget=forms.HiddenInput)
