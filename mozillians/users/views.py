import datetime

from django.contrib import auth, messages
from django.shortcuts import redirect, render

import commonware.log
from funfactory.urlresolvers import reverse
from tower import ugettext as _

from mozillians.common.decorators import allow_public, allow_unvouched
from mozillians.phonebook.forms import RegisterForm, UserForm
from mozillians.phonebook.models import Invite


log = commonware.log.getLogger('m.users')
get_invite = lambda c: Invite.objects.get(code=c, redeemed=None)


@allow_unvouched
def logout(request, **kwargs):
    """Logout view that wraps Django's logout but always redirects.

    Django's contrib.auth.views logout method renders a template if
    the `next_page` argument is `None`, which we don't want. This view
    always returns an HTTP redirect instead.

    """
    return auth.views.logout(request, next_page=reverse('home'), **kwargs)


@allow_public
def register(request):
    """Registers Users.

    Pulls out an invite code if it exists and auto validates the user
    if so. Single-purpose view.
    """
    if 'code' in request.GET:
        request.session['invite-code'] = request.GET['code']
    return redirect('home')


def _update_invites(request):
    code = request.session.get('invite-code')
    if code:
        try:
            invite = get_invite(code)
            voucher = invite.inviter
        except Invite.DoesNotExist:
            msg = 'Invite code [%s], does not exist!' % code
            log.warning(msg)
            # If there is no invite, lets get out of here.
            return
    else:
        # If there is no invite, lets get out of here.
        return

    redeemer = request.user.get_profile()
    redeemer.vouch(voucher)
    invite.redeemed = datetime.datetime.now()
    invite.redeemer = redeemer
    invite.send_thanks()
    invite.save()
