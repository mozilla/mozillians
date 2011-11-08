from django.contrib.auth.models import User

import commonware.log
import cronjobs

from users.models import UserProfile
import larper

log = commonware.log.getLogger('m.user')


@cronjobs.register
def vouchify():
    """Synchronizes LDAP vouch info into database.

    This queries LDAP for users who's corresponding ``UserProfile`` has
    ``is_vouched`` as ``False``.  It then updates ``is_vouched`` and
    ``vouched_by`` with up-to-date data.
    """
    users = UserProfile.objects.filter(is_vouched=False)

    for user in users:
        person = user.get_ldap_person()
        if 'mozilliansVouchedBy' in person[1]:
            user.is_vouched = True
            voucher = (person[1]['mozilliansVouchedBy'][0].split(',')[0]
                                                          .split('=')[1])
            by = larper.get_user_by_uid(voucher)
            if by:
                email = by[1]['mail'][0]
                try:
                    user.vouched_by = User.objects.get(email=email)
                except User.DoesNotExist:
                    log.warning('No matching user for %s' % email)
            user.save()
            log.info('Data copied for %s' % user.user.username)
        log.debug('%s is still unvouched... skipping' % user.user.username)
