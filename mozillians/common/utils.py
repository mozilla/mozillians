import sys

from django.conf import settings

import requests
import waffle
from nameparser import HumanName


def absolutify(url):
    """Takes a URL and prepends the SITE_URL"""
    site_url = getattr(settings, 'SITE_URL', False)

    # If we don't define it explicitly
    if not site_url:
        protocol = settings.PROTOCOL
        hostname = settings.DOMAIN
        port = settings.PORT
        if (protocol, port) in (('https://', 443), ('http://', 80)):
            site_url = ''.join(map(str, (protocol, hostname)))
        else:
            site_url = ''.join(map(str, (protocol, hostname, ':', port)))

    return site_url + url


def akismet_spam_check(user_ip, user_agent, **optional):
    """Checks for spam content against Akismet API."""

    AKISMET_API_KEY = getattr(settings, 'AKISMET_API_KEY', '')
    AKISMET_CHECK_ENABLED = waffle.switch_is_active('AKISMET_CHECK_ENABLED')

    if not AKISMET_API_KEY or not AKISMET_CHECK_ENABLED:
        return None

    AKISMET_URL = 'https://{0}.rest.akismet.com/1.1/comment-check'.format(AKISMET_API_KEY)

    parameters = {
        'blog': settings.SITE_URL,
        'user_ip': user_ip,
        'user_agent': user_agent,
    }

    parameters.update(optional)

    response = requests.post(AKISMET_URL, data=parameters)
    response.raise_for_status()

    try:
        return {'true': True, 'false': False}[response.text]
    except KeyError:
        error = response.headers.get('x-akismet-debug-help')
        raise Exception('Akismet raised an error: {0}'.format(error))


def is_test_environment():
    """Check if environment is a test runner."""
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        return True

    if settings.DEV:
        return True
    return False


def bundle_profile_data(profile_id, delete=False):
    """Packs all the Identity Profiles of a user into a dictionary."""
    from mozillians.common.templatetags.helpers import get_object_or_none
    from mozillians.users.models import IdpProfile, UserProfile

    try:
        profile = UserProfile.objects.get(pk=profile_id)
    except UserProfile.DoesNotExist:
        return []
    human_name = HumanName(profile.full_name)

    primary_idp = get_object_or_none(IdpProfile, profile=profile, primary=True)
    primary_login_email = profile.email
    if primary_idp:
        primary_login_email = primary_idp.email

    results = []
    for idp in profile.idp_profiles.all():

        data = {
            'user_id': idp.auth0_user_id,
            'timezone': profile.timezone,
            'active': profile.user.is_active,
            'lastModified': profile.last_updated.isoformat(),
            'created': profile.user.date_joined.isoformat(),
            'userName': profile.user.username,
            'displayName': profile.display_name,
            'primaryEmail': primary_login_email,
            'emails': profile.get_cis_emails(),
            'uris': profile.get_cis_uris(),
            'picture': profile.get_photo_url(),
            'shirtSize': profile.get_tshirt_display() or '',
            'groups': [] if delete else profile.get_cis_groups(idp),
            'tags': [] if delete else profile.get_cis_tags(),

            # Derived fields
            'firstName': human_name.first,
            'lastName': human_name.last,

            # Hardcoded fields
            'preferredLanguage': 'en_US',
            'phoneNumbers': [],
            'nicknames': [],
            'SSHFingerprints': [],
            'PGPFingerprints': [],
            'authoritativeGroups': []
        }
        results.append(data)
    return results
