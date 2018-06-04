import time
from urlparse import urlparse

from django.conf import settings

from authzero import AuthZero


class MozilliansAuthZeroManagement(object):

    def __init__(self):
        o = urlparse(settings.OIDC_OP_TOKEN_ENDPOINT)
        self.client = AuthZero({
            'client_id': settings.OIDC_RP_CLIENT_ID,
            'client_secret': settings.OIDC_RP_CLIENT_SECRET,
            'uri': o.netloc
        })

    def change_primary_identiy(self, auth0_id, primary=False):
        """Toggle status in the primary auth0 login identity."""
        self.get_access_token()
        user_schema = self.client.get_user(auth0_id)
        app_metadata = user_schema.get('app_metadata', {})
        app_metadata['mozilliansorg_primary'] = primary
        return self.client.update_user(auth0_id, app_metadata)

    def get_access_token(self):
        """Handle the access_token.

        Re-use the existing token if it's valid else
        get a new one.
        """
        token = self.client.access_token
        # Check if there is an existing token and if yes if it's valid
        if not token or not self.client.access_token_valid_until < time.time():
            return self.client.get_access_token()
        return token
