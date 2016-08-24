from django.conf import settings

import requests
import waffle


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
