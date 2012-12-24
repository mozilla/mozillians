import json

try:
    from django.conf import settings
    BASKET_URL = settings.BASKET_URL
except (ImportError, AttributeError):
    BASKET_URL = 'http://localhost:8000'

import requests


class BasketException(Exception):
    pass


def basket_url(method, token=None):
    """Form a basket API url. If the request requires a user-specific
    token, it is suffixed as the last part of the URL."""

    token = '%s/' % token if token else ''

    return ('%s/news/%s/%s' % (BASKET_URL, method, token))

def parse_response(res):
    """Parse the result of a basket API call, raise exception on error"""

    if res.status_code != 200:
        raise BasketException('%s request returned from basket: %s' %
                              (res.status_code, res.content))

    # Parse the json and check for errors
    result = json.loads(res.content)

    if result.get('status') == 'error':
        raise BasketException(result['desc'])

    return result


def request(method, action, data=None, token=None, params=None):
    """Call the basket API with the supplied http method and data."""

    # newsletters should be comma-delimited
    if data and 'newsletters' in data:
        if '__iter__' in data['newsletters']:
            data['newsletters'] = ','.join(data['newsletters'])

    try:
        res = requests.request(method,
                               basket_url(action, token),
                               data=data,
                               params=params,
                               timeout=10)
    except requests.exceptions.ConnectionError:
        raise BasketException("Error connecting to basket")
    return parse_response(res)


# Public API methods

def subscribe(email, newsletters, **kwargs):
    """Subscribe an email through basket to `newsletters`, which can
    be string or an array of newsletter names. Additional parameters
    should be passed as keyword arguments."""

    kwargs.update(email=email, newsletters=newsletters)
    return request('post', 'subscribe', data=kwargs)


def send_sms(mobile_number, msg_name, optin=False):
    """
    Send SMS message `msg_name` to `mobile_number` and optionally add the
    number to a list for future messages.
    """
    return request('post', 'subscribe_sms', data={
        'mobile_number': mobile_number,
        'msg_name': msg_name,
        'optin': 'Y' if optin else 'N',
    })


def unsubscribe(token, email, newsletters=None, optout=False):
    """Unsubscribe an email from certain newsletters, or all of them
    if `optout` is passed. Requires a token."""

    data = {'email': email}

    if optout:
        data['optout'] = 'Y'
    elif newsletters:
        data['newsletters'] = newsletters
    else:
        raise BasketException('unsubscribe requires ether a newsletters '
                              'or optout parameter')

    return request('post', 'unsubscribe', data=data, token=token)


def user(token):
    """Get all the information about a user. Requires a token."""
    return request('get', 'user', token=token)


def update_user(token, **kwargs):
    """Update any fields for a user. Requires a token. If newsletters
    is passed, the user is only subscribed to those specific
    newsletters."""

    return request('post', 'user', data=kwargs, token=token)


def debug_user(email, supertoken):
    """Get a user's information using a supertoken only known by devs,
    useful for ensuring that data is being posted correctly"""

    return request('get', 'debug-user',
                   params={'email': email,
                           'supertoken': supertoken})
