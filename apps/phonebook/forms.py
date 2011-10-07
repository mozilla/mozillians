import tempfile

from django import forms
from django.conf import settings

import happyforms
import Image
from easy_thumbnails import processors
from tower import ugettext as _, ugettext_lazy as _lazy

from phonebook.models import Invite


class SearchForm(happyforms.Form):
    q = forms.CharField(widget=forms.HiddenInput, required=True)


class ProfileForm(happyforms.Form):
    first_name = forms.CharField(label=_lazy(u'First Name'), required=False)
    last_name = forms.CharField(label=_lazy(u'Last Name'), required=True)
    biography = forms.CharField(label=_lazy(u'Bio'),
                                widget=forms.Textarea(),
                                required=False)
    photo = forms.ImageField(label=_lazy(u'Profile Photo'), required=False)

    # Remote System Ids
    # Tightly coupled with larper.UserSession.form_to_service_ids_attrs
    irc_nickname = forms.CharField(label=_lazy(u'IRC Nickname'),
                                   required=False)
    irc_nickname_unique_id = forms.CharField(widget=forms.HiddenInput,
                                             required=False)

    def clean_photo(self):
        """Let's make sure things are right.

        Cribbed from zamboni.  Thanks Dave Dash!

        TODO: this needs to go into celery

        - File IT bug for celery
        - Ensure files aren't InMemory files
        - See zamboni.apps.users.forms
        """
        photo = self.cleaned_data['photo']

        if not photo:
            return

        if photo.content_type not in ('image/png', 'image/jpeg'):
            raise forms.ValidationError(
                    _('Images must be either PNG or JPG.'))

        if photo.size > settings.MAX_PHOTO_UPLOAD_SIZE:
            raise forms.ValidationError(
                    _('Please use images smaller than %dMB.' %
                      (settings.MAX_PHOTO_UPLOAD_SIZE / 1024 / 1024 - 1)))

        im = Image.open(photo)
        # Resize large images
        if any(d > 300 for d in im.size):
            im = processors.scale_and_crop(im, (300, 300), crop=True)
        fn = tempfile.mktemp(suffix='.jpg')
        f = open(fn, 'w')
        im.save(f, 'JPEG')
        f.close()
        photo.file = open(fn)
        return photo


class DeleteForm(happyforms.Form):
    unique_id = forms.CharField(widget=forms.HiddenInput)


class VouchForm(happyforms.Form):
    """Vouching is captured via a user's unique_id."""
    voucher = forms.CharField(widget=forms.HiddenInput)
    vouchee = forms.CharField(widget=forms.HiddenInput)


class InviteForm(happyforms.ModelForm):
    class Meta:
        model = Invite
