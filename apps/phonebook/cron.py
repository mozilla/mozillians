from django.contrib.auth.models import User

import commonware.log
import cronjobs

from models import Invite

log = commonware.log.getLogger('m.cron')


@cronjobs.register
def invite(filename):
    f = open(filename)
    for addr in f.xreadlines():
        addr = addr.strip()
        invites = Invite.objects.filter(recipient=addr)
        users = User.objects.filter(email=addr)

        # Don't invite people in the system, or who have been invited.
        if invites.count() or users.count():
            log.info('%s already invited or in the system' % addr)
            continue

        i = Invite.objects.create(inviter='ZUUL', recipient=addr)
        i.send()
        log.info('Invited %s' % addr)
