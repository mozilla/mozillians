import datetime

from mozillians.phonebook.models import Invite


def update_invites(request):
    code = request.session.get('invite-code')
    if code:
        try:
            invite = Invite.objects.get(code=code, redeemed=None)
            voucher = invite.inviter
        except Invite.DoesNotExist:
            return
    else:
        # If there is no invite, lets get out of here.
        return

    redeemer = request.user.userprofile
    redeemer.vouch(voucher)
    invite.redeemed = datetime.datetime.now()
    invite.redeemer = redeemer
    invite.send_thanks()
    invite.save()
