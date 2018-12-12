import datetime

from mozillians.phonebook.models import Invite
from mozillians.users.models import IdpProfile


def redeem_invite(redeemer, code):
    if code:
        try:
            invite = Invite.objects.get(code=code, redeemed=None)
            voucher = invite.inviter
        except Invite.DoesNotExist:
            return
    else:
        # If there is no invite, lets get out of here.
        return

    redeemer.vouch(voucher, invite.reason)
    invite.redeemed = datetime.datetime.now()
    invite.redeemer = redeemer
    invite.send_thanks()
    invite.save()


def get_profile_link_by_email(email):
    try:
        idp_profile = IdpProfile.objects.get(email=email, primary=True)
    except (IdpProfile.DoesNotExist, IdpProfile.MultipleObjectsReturned):
        return ''
    else:
        return idp_profile.profile.get_absolute_url()
