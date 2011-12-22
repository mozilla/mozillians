import hashlib
import os
import sys

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist

import commonware.log
import cronjobs
from celery.task.sets import TaskSet
from celeryutils import chunked

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


# TODO: Remove after we can safely say that LDAP is gone.
@cronjobs.register
def fix_bad_ldap_vouch():
    """Synchronizes MySQL vouch data into broken LDAP accounts.

    Just vouches them as ZUUL because the MySQL vouch data is good and what
    we'll use going forward.
    """
    users = UserProfile.objects.filter(is_vouched=True)

    for user in users:
        person = user.get_ldap_person()

        if person:
            try:
                larper.record_vouch('ZUUL', person[1]['uniqueIdentifier'][0])
            except TYPE_OR_VALUE_EXISTS:
                log.info('User is already vouched; no big.')


@cronjobs.register
def flee_ldap():
    """Copies data from LDAP into UserProfile."""
    profiles = UserProfile.objects.all()

    for profile in profiles:
        person = profile.get_ldap_person()
        username = person[1]['uniqueIdentifier'][0]
        if 'description' in person[1]:
            bio = person[1]['description'][0]
        if 'jpegPhoto' in person[1]:
            photo = person[1]['jpegPhoto'][0]
        lastname = person[1]['sn'][0]
        firstname = ''
        if 'givenName' in person[1]:
            firstname = person[1]['givenName'][0]
        displayname = person[1]['displayName'][0]
        service_data = larper.get_service_data(username)

        ircname = ''
        if service_data:
            ircname = service_data['irc://irc.mozilla.org/'].service_id

        if photo:
            # ensure the netapp storage exists
            if not os.path.exists(settings.NETAPP_STORAGE):
                log.error('Netapp storage not found at %s'
                           % settings.NETAPP_STORAGE)
                sys.exit(1)

            # if userpic dir doesn't exist make it
            if not os.path.exists(settings.USERPICS_PATH):
                os.mkdir(settings.USERPICS_PATH)

            destination = os.path.join(settings.USERPICS_PATH, '%d.jpg' %
                                       profile.user_id)

            md5 = lambda x: hashlib.md5(x).hexdigest()

            write_it = True
            # see if file already exists for user
            if os.path.exists(destination):
                # if it does compare it
                ldap_hash = md5(photo)
                existing_hash = md5(open(destination).read())
                if ldap_hash == existing_hash:
                    # if same log debug
                    log.debug('File already dumped for user: %d' %
                              profile.user_id)
                    write_it = False
                else:
                    # if different log warning and copy it
                    log.warning('Different file in place for user: %d' %
                                profile.user_id)
                    os.rename(destination, destination + '.' + existing_hash)

            if write_it:
                with open(destination, 'w') as f:
                    f.write(photo)

        profile.user.username = username
        profile.user.lastname = lastname
        profile.user.firstname = firstname
        profile.bio = bio
        profile.photo = bool(photo)
        profile.display_name = displayname
        profile.ircname = ircname
        profile.user.save()
        profile.save()
        log.debug('u:%d saved' % profile.user_id)


@cronjobs.register
def index_all_profiles():
    from elasticutils import tasks

    ids = (UserProfile.objects.values_list('id', flat=True))
    ts = [tasks.index_objects.subtask(args=[UserProfile, chunk])
          for chunk in chunked(sorted(list(ids)), 150)]
    TaskSet(ts).apply_async()
