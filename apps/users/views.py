import datetime

from django.contrib import auth, messages
from django.shortcuts import redirect, render

import commonware.log
from funfactory.urlresolvers import reverse
from tower import ugettext as _

from apps.common.decorators import allow_public, allow_unvouched
from apps.phonebook.forms import RegisterForm, UserForm
from apps.phonebook.models import Invite


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

    user = request.user
    if not user.is_authenticated() or user.userprofile.is_complete:
        return redirect('home')

    user_form = UserForm(request.POST or None, instance=user)
    profile_form = RegisterForm(request.POST or None,
                                instance=user.get_profile())

    if (user_form.is_valid() and profile_form.is_valid()):
        user_form.save()
        profile_form.save()
        auth.login(request, user)
        _update_invites(request)
        messages.info(request, _(u'Your account has been created.'))
        return redirect(reverse('profile', args=[request.user.username]))

    # 'user' object must be passed in because we are not logged in
    return render(request, 'registration/register.html',
                  dict(profile_form=profile_form,
                       user_form=user_form,
                       edit_form_action=reverse('register'),
                       mode='new',
                       profile=user.get_profile(),
                       user=user))


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
