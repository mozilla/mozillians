import tempfile

from django import forms
from django.conf import settings

import happyforms
import Image
from easy_thumbnails import processors
from tower import ugettext as _

from phonebook.helpers import vouched
from phonebook.models import Invite
from groups.models import SYSTEM_GROUP_CHARACTER, Group


class SearchForm(happyforms.Form):
    q = forms.CharField(widget=forms.HiddenInput, required=True)


class ProfileForm(happyforms.Form):
    first_name = forms.CharField(label=_(u'First Name'), required=False)
    last_name = forms.CharField(label=_(u'Last Name'), required=True)
    biography = forms.CharField(label=_(u'Bio'),
                                widget=forms.Textarea(),
                                required=False)
    photo = forms.ImageField(label=_(u'Profile Photo'), required=False)

    # Remote System Ids
    # Tightly coupled with larper.UserSession.form_to_service_ids_attrs
    irc_nickname = forms.CharField(label=_(u'IRC Nickname'),
                                   required=False)
    irc_nickname_unique_id = forms.CharField(widget=forms.HiddenInput,
                                             required=False)

    groups = forms.CharField(label=_(u'Groups'), required=False)

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

    def clean_groups(self):
        """Groups are saved in lowercase because it's easy and consistent."""
        return [g for g in self.cleaned_data['groups'].lower().split()
                if SYSTEM_GROUP_CHARACTER not in g]

    def save(self, request, ldap):
        """Save this form to both LDAP and RDBMS backends, as appropriate."""
        # Save stuff in LDAP first...
        # TODO: Find out why this breaks the larper tests
        # ldap.update_person(request.user.unique_id, self.cleaned_data)
        # ldap.update_profile_photo(request.user.unique_id, self.cleaned_data)

        # ... then save other stuff in RDBMS.
        self._save_groups(request)

    def _save_groups(self, request):
        """Parse a string of (usually space-demilited) groups and save them."""
        # If this user isn't vouched they can't edit their groups.
        if not vouched(request.user):
            return

        profile = request.user.get_profile()

        # If no groups are supplied, we're deleting all non-hidden,
        # non-special groups.
        if not self.cleaned_data['groups']:
            profile.groups.filter(system=False).delete()
            return

        # Remove any non-hidden groups that weren't supplied in this list.
        profile.groups.remove(*[g for g in profile.groups.filter(system=False)
                                if g.name not in self.cleaned_data['groups']])

        # Add/create the rest of the groups
        groups_to_add = []
        for g in self.cleaned_data['groups']:
            (group, created) = Group.objects.get_or_create(name=g)
            groups_to_add.append(group)

        profile.groups.add(*groups_to_add)

class DeleteForm(happyforms.Form):
    unique_id = forms.CharField(widget=forms.HiddenInput)


class VouchForm(happyforms.Form):
    """Vouching is captured via a user's unique_id."""
    vouchee = forms.CharField(widget=forms.HiddenInput)


class InviteForm(happyforms.ModelForm):
    class Meta:
        model = Invite
