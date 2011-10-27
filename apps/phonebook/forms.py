import tempfile

from django import forms
from django.conf import settings

import happyforms
import Image
from easy_thumbnails import processors
from tower import ugettext as _, ugettext_lazy as _lazy

from phonebook.helpers import vouched
from phonebook.models import Invite
from tags.models import Tag


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

    tags = forms.CharField(label=_lazy(u'Tags'), required=False,
                           widget=forms.TextInput())

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

    def clean_tags(self):
        """All tags are saved in lowercase because it's easy and consistent."""
        return [t.lower() for t in self.cleaned_data['tags'].split(u' ')]

    def save_tags(self, request):
        """Parse a string of (usually space-demilited) tags and save them."""
        # If this user isn't vouched they can't edit their tags.
        if not vouched(request.user):
            return

        profile = request.user.get_profile()

        # If no tags are supplied, we're deleting all non-hidden,
        # non-special tags.
        if not len(self.cleaned_data['tags']):
            tags_to_remove = profile.tags.filter(hidden=False)
            profile.tags.remove(*tags_to_remove)
            return

        current_tags = profile.tags.filter(hidden=False)
        tags_to_remove = []

        # Remove any non-hidden tags that weren't supplied in this list.
        if len(current_tags):
            for t in current_tags:
                if t not in [tag.name for tag in current_tags]:
                    tags_to_remove.append(tag)

            if len(tags_to_remove):
                profile.tags.remove(*tags_to_remove)

        # Add/create the rest of the tags
        for t in self.cleaned_data['tags']:
            try:
                tag = Tag.objects.get(name__iexact=t)
                profile.tags.add(tag)
            except Tag.DoesNotExist:
                profile.tags.create(name=t)

class DeleteForm(happyforms.Form):
    unique_id = forms.CharField(widget=forms.HiddenInput)


class VouchForm(happyforms.Form):
    """Vouching is captured via a user's unique_id."""
    vouchee = forms.CharField(widget=forms.HiddenInput)


class InviteForm(happyforms.ModelForm):
    class Meta:
        model = Invite
