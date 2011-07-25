from django import forms

from tower import ugettext as _

class SearchForm(forms.Form):
    q = forms.CharField(widget=forms.HiddenInput, required=False)

class ProfileForm(forms.Form):
    first_name = forms.CharField(label=_('First Name'), required=False)
    last_name = forms.CharField(label=_('Last Name'), required=True)
    biography = forms.CharField(label=_('Bio'), 
                                widget=forms.Textarea(),
                                required=False)
    #photo

class VouchForm(forms.Form):
    """ Vouching is captured via a user's uniqueIdentifier """
    voucher = forms.CharField(widget=forms.HiddenInput)
    vouchee = forms.CharField(widget=forms.HiddenInput)
