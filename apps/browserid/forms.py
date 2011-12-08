from django import forms

from django_browserid.forms import BrowserIDForm


class ModalBrowserIdForm(BrowserIDForm):
    """Form to capture user's intention when logging in."""
    mode = forms.CharField(widget=forms.HiddenInput)
