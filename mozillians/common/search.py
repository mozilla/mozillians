import boto3
import os

from botocore.auth import SigV4Auth
from requests_aws4auth import AWS4Auth
from elasticsearch import RequestsHttpConnection


class AWS4AuthEncoded(AWS4Auth):
    def __call__(self, request):
        request = super(AWS4AuthEncoded, self).__call__(request)

        for header_name in request.headers:
            self._encode_header_to_utf8(request, header_name)

        return request

    def _encode_header_to_utf8(self, request, header_name):
        value = request.headers[header_name]

        if isinstance(value, unicode):
            value = value.encode('utf-8')

        if isinstance(header_name, unicode):
            del request.headers[header_name]
            header_name = header_name.encode('utf-8')

        request.headers[header_name] = value


class AWSRequestsHttpConnection(RequestsHttpConnection):
    def perform_request(self, *args, **kwargs):
        credentials = boto3.session.Session().get_credentials()
        signed_creds = SigV4Auth(credentials, 'es', os.environ['AWS_ES_REGION'])

        secure_auth = AWS4AuthEncoded(
            credentials.access_key, credentials.secret_key,
            os.environ['AWS_ES_REGION'], 'es',
            session_token=signed_creds.credentials.token
        )
        self.session.auth = secure_auth
        return super(AWSRequestsHttpConnection, self).perform_request(*args, **kwargs)
