from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist

import commonware.log
import cronjobs

import larper
from users.models import UserProfile

log = commonware.log.getLogger('m.cron')


@cronjobs.register
def create_missing_profiles():
    """Create missing profiles on dev/stage.

    The dev/staging servers are missing certain User objects, likely because
    of users created before our UserProfile signal receivers. This will
    create them and prevent us from getting annoying tracebacks from tests.
    """
    users = User.objects.all()

    for u in users:
        try:
            u.get_profile()
        except ObjectDoesNotExist:
            log.info('Created profile for user with email %s' % u.email)
            UserProfile.objects.create(user=u)


@cronjobs.register
def create_missing_users():
    """Create missing users on dev/stage.

    The dev/staging servers are missing certain User objects, likely because
    of users created before our UserProfile signal receivers. This will
    create them and prevent us from getting annoying tracebacks from tests.

    Note that this needs to be run with the LDAP limit (temporarily) disabled.
    """
    users = larper._return_all()
    users_created = []

    for u in users:
        email = u[1]['mail'][0]
        if not User.objects.filter(email=email):
            try:
                User.objects.create(username=email, email=email)
                users_created.append(email)
                log.info('Created user for LDAPer with email %s' % email)
            except:
                log.info('Could not create user for LDAPer with email %s'
                         % email)

    log.info('Created %s users' % len(users_created))


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
        if person and 'mozilliansVouchedBy' in person[1]:
            user.is_vouched = True
            voucher = (person[1]['mozilliansVouchedBy'][0].split(',')[0]
                                                          .split('=')[1])
            by = larper.get_user_by_uid(voucher)
            if by:
                email = by[1]['mail'][0]
                try:
                    user.vouched_by = (User.objects.get(email=email)
                                                   .get_profile())
                except User.DoesNotExist:
                    log.warning('No matching user for %s' % email)
                except UserProfile.DoesNotExist:
                    log.warning('No matching user_profile for %s' % email)
            user.save()
            log.info('Data copied for %s' % user.user.username)
        log.debug('%s is still unvouched... skipping' % user.user.username)
