import json
import graphene
import requests

from django.conf import settings

from mozillians.graphql_profiles.utils import json2obj, parse_datetime_iso8601


class Alg(graphene.Enum):
    """V2 Schema Alg object for Graphene."""

    HS256 = 'HS256'
    RS256 = 'RS256'
    RSA = 'RSA'
    ED25519 = 'ED25519'


class Typ(graphene.Enum):
    """V2 Schema Typ object for Graphene."""

    JWT = 'JWT'
    PGP = 'PGP'


class Classification(graphene.Enum):
    """V2 Schema Classification object for Graphene."""

    MOZILLA_CONFIDENTIAL = 'MOZILLA CONFIDENTIAL'
    PUBLIC = 'PUBLIC'
    INDIVIDUAL_CONFIDENTIAL = 'INDIVIDUAL CONFIDENTIAL'
    STAFF_ONLY = 'WORKGROUP CONFIDENTIAL: STAFF ONLY'


class PublisherAuthority(graphene.Enum):
    """V2 Schema PublisherAuthority object for Graphene."""

    LDAP = 'ldap'
    MOZILLIANS = 'mozilliansorg'
    HRIS = 'hris'
    CIS = 'cis'
    ACCESS_PROVIDER = 'access_provider'


class Publisher(graphene.ObjectType):
    """V2 Schema Publisher object for Graphene."""

    alg = graphene.Field(Alg)
    typ = graphene.Field(Typ)
    value = graphene.String()
    name = graphene.Field(PublisherAuthority)


class Signature(graphene.ObjectType):
    """V2 Schema Signature object for Graphene."""

    publisher = graphene.Field(Publisher)
    additional = graphene.List(Publisher)


class Metadata(graphene.ObjectType):
    """V2 Schema Metadata object for Graphene."""

    classification = graphene.Field(Classification)
    last_modified = graphene.DateTime()
    created = graphene.DateTime()
    verified = graphene.Boolean()

    def resolve_last_modified(self, info, **kwargs):
        """Resolver to return a datetime object."""
        return parse_datetime_iso8601(self.get('last_modified'))

    def resolve_created(self, info, **kwargs):
        """Resolver to return a datetime object."""
        return parse_datetime_iso8601(self.get('created'))


class BaseObjectType(graphene.ObjectType):
    """V2 Schema Base object object for Graphene."""
    signature = graphene.Field(Signature)
    metadata = graphene.Field(Metadata)


class StandardAttributeDatetime(BaseObjectType):
    """V2 Schema StandardAttributeDatetime object for Graphene."""

    value = graphene.DateTime()

    def resolve_value(self, info, **kwargs):
        """Resolver to return a datetime object."""
        return parse_datetime_iso8601(self.get('value'))


class StandardAttributeBoolean(BaseObjectType):
    """V2 Schema StandardAttributeBoolean object for Graphene."""

    value = graphene.Boolean()


class StandardAttributeString(BaseObjectType):
    """V2 Schema StandardAttributeString object for Graphene."""

    value = graphene.String()


class IdentitiesValues(graphene.ObjectType):
    """V2 Schema IdentitiesValues object for Graphene."""

    github_id_v3 = graphene.String()
    github_id_v4 = graphene.String()
    LDAP = graphene.String()
    bugzilla = graphene.String()
    google = graphene.String()
    firefoxaccounts = graphene.String()
    emails = graphene.List(graphene.String)

    def resolve_bugzilla(self, info, **kwargs):
        """Custom resolver for the Bugzilla Identity.

        Extract the bugzilla.mozilla.org Identity from the profile v2 schema.
        """
        return self.get('bugzilla.mozilla.org')

    def resolve_google(self, info, **kwargs):
        """Custom resolver for the Google Identity.

        Extract the google-oauth2 Identity from the profile v2 schema.
        """
        return self.get('google-oauth2')


class Identities(BaseObjectType):
    """V2 Schema Identities object for Graphene."""

    values = graphene.Field(IdentitiesValues)

    def resolve_values(self, info, **kwargs):
        return self.get('values')


class StandardAttributeValues(BaseObjectType):
    """V2 Schema StandardAttributeValues object for Graphene."""

    values = graphene.List(graphene.String)

    def resolve_values(self, info, **kwargs):
        """Custom resolver for the list of values."""
        if isinstance(self['values'], list):
            return self['values']
        values = self.get('values')
        if values:
            return values.items()
        return None


class AccessInformation(graphene.ObjectType):
    """V2 Schema AccessInformation object for Graphene."""

    ldap = graphene.Field(StandardAttributeValues)
    mozilliansorg = graphene.Field(StandardAttributeValues)
    access_provider = graphene.Field(StandardAttributeValues)


class RelatedProfile(graphene.ObjectType):
    """RelatedProfile object for Graphene.

    This is not compatible with v2 schema.
    It's used to display relations in orgchart.
    """
    user_id = graphene.String(required=True)
    first_name = graphene.String(required=True)
    last_name = graphene.String(required=True)
    picture = graphene.String(required=True)
    title = graphene.String(required=True)
    fun_title = graphene.String(required=True)
    location = graphene.String(required=True)


class Profile(graphene.ObjectType):
    """V2 Schema Profile object for Graphene.

    Combines Core and Extended Profile attributes from the V2 Schema.
    """

    user_id = graphene.Field(StandardAttributeString)
    login_method = graphene.Field(StandardAttributeString)
    active = graphene.Field(StandardAttributeBoolean)
    last_modified = graphene.Field(StandardAttributeDatetime)
    created = graphene.Field(StandardAttributeDatetime)
    usernames = graphene.Field(StandardAttributeValues)
    first_name = graphene.Field(StandardAttributeString)
    last_name = graphene.Field(StandardAttributeString)
    primary_email = graphene.Field(StandardAttributeString)
    identities = graphene.Field(Identities)
    ssh_public_keys = graphene.Field(StandardAttributeValues)
    pgp_public_keys = graphene.Field(StandardAttributeValues)
    access_information = graphene.Field(AccessInformation)
    fun_title = graphene.Field(StandardAttributeString)
    description = graphene.Field(StandardAttributeString)
    location_preference = graphene.Field(StandardAttributeString)
    office_location = graphene.Field(StandardAttributeString)
    timezone = graphene.Field(StandardAttributeString)
    preferred_language = graphene.Field(StandardAttributeValues)
    tags = graphene.Field(StandardAttributeValues)
    pronouns = graphene.Field(StandardAttributeString)
    picture = graphene.Field(StandardAttributeString)
    uris = graphene.Field(StandardAttributeValues)
    phone_numbers = graphene.Field(StandardAttributeValues)
    alternative_name = graphene.Field(StandardAttributeString)
    manager = graphene.Field(RelatedProfile)
    directs = graphene.List(RelatedProfile)
    # HRIS values
    employee_id = graphene.Field(StandardAttributeString)
    business_title = graphene.Field(StandardAttributeString)
    is_manager = graphene.Field(StandardAttributeBoolean)
    is_director_or_above = graphene.Field(StandardAttributeBoolean)
    entity = graphene.Field(StandardAttributeString)
    team = graphene.Field(StandardAttributeString)
    cost_center = graphene.Field(StandardAttributeString)
    worker_type = graphene.Field(StandardAttributeString)
    primary_work_email = graphene.Field(StandardAttributeString)
    wpr_desk_number = graphene.Field(StandardAttributeString)
    public_email_addresses = graphene.Field(StandardAttributeValues)


class Vouches(graphene.ObjectType):
    """Schema to expose user vouches."""
    description = graphene.String()
    voucher = graphene.Field(Profile)
    autovouch = graphene.Boolean()
    date = graphene.DateTime()

    def resolve_description(self, info, **kwargs):
        return self.description

    def resolve_autovouch(self, info, **kwargs):
        return self.autovouch

    def resolve_date(self, info, **kwargs):
        return self.date

    def resolve_voucher(self, info, **kwargs):
        voucher_user_id = self.voucher.auth0_user_id
        resp = requests.get(settings.V2_PROFILE_ENDPOINT).json()

        data = json2obj(json.dumps(resp))
        for profile in data:
            if profile['user_id']['value'] == voucher_user_id:
                return profile
        return None
