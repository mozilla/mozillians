from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist

import commonware.log
import cronjobs

import larper
from .models import UserProfile


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
