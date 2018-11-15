import graphene

from graphene.types import generic

from mozillians.graphql_profiles.resolvers import dino_park_resolver
from mozillians.graphql_profiles.utils import parse_datetime_iso8601, retrieve_v2_profile


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


class Display(graphene.Enum):
    """V2 Schema privacy information object for Graphene."""

    PUBLIC = 'public'
    AUTHENTICATED = 'authenticated'
    VOUCHED = 'vouched'
    NDAED = 'ndaed'
    STAFF = 'staff'
    PRIVATE = 'private'


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
    display = graphene.Field(Display)

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

    ldap = generic.GenericScalar()
    mozilliansorg = generic.GenericScalar()
    access_provider = generic.GenericScalar()
    hris = generic.GenericScalar()

    class Meta:
        default_resolver = dino_park_resolver


class StaffInformation(graphene.ObjectType):
    """V2 Schema with Staff data for Graphene."""
    manager = graphene.Boolean()
    director = graphene.Boolean()
    staff = graphene.Boolean()
    title = graphene.String()
    team = graphene.String()
    cost_center = graphene.String()
    worker_type = graphene.String()
    wpr_desk_number = graphene.String()
    office_location = graphene.String()

    class Meta:
        default_resolver = dino_park_resolver


class Identities(BaseObjectType):
    """V2 Schema Identities object for Graphene."""

    github_id_v3 = graphene.String()
    github_id_v4 = graphene.String()
    dinopark_id = graphene.String()
    mozilliansorg_id = graphene.String()
    mozilla_ldap_id = graphene.String()
    bugzilla_mozilla_org_id = graphene.String()
    mozilla_posix_id = graphene.String()
    firefox_accounts_id = graphene.String()
    google_oauth2_id = graphene.String()

    class Meta:
        default_resolver = dino_park_resolver


class RelatedProfile(graphene.ObjectType):
    """RelatedProfile object for Graphene.

    This is not compatible with v2 schema.
    It's used to display relations in orgchart.
    """
    user_id = graphene.String()
    first_name = graphene.String()
    last_name = graphene.String()
    picture = graphene.String()
    title = graphene.String()
    fun_title = graphene.String()
    location = graphene.String()


class AbstractProfile(graphene.AbstractType):
    """V2 Abstract Schema Profile object for Graphene.

    Generic Scalars are used when the attribute value is not know before hand.
    The result is a dictionary of attributes with values. eg
    usernames: {'attribute1: value1, 'attribute2': value2}
    """
    user_id = graphene.String()
    login_method = graphene.String()
    username = graphene.String()
    active = graphene.Boolean()
    last_modified = graphene.DateTime()
    created = graphene.DateTime()
    usernames = generic.GenericScalar()
    pronouns = graphene.String()
    first_name = graphene.String()
    last_name = graphene.String()
    alternative_name = graphene.String()
    primary_email = graphene.String()
    identities = graphene.Field(Identities)
    ssh_public_keys = generic.GenericScalar()
    pgp_public_keys = generic.GenericScalar()
    access_information = graphene.Field(AccessInformation)
    fun_title = graphene.String()
    description = graphene.String()
    location = graphene.String()
    timezone = graphene.String()
    languages = graphene.List(graphene.String)
    tags = graphene.List(graphene.String)
    picture = graphene.String()
    uris = generic.GenericScalar()
    phone_numbers = generic.GenericScalar()
    staff_information = graphene.Field(StaffInformation)


class Vouches(graphene.ObjectType):
    """Schema to expose user vouches."""
    description = graphene.String()
    voucher = graphene.Field('mozillians.graphql_profiles.schema.Profile')
    autovouch = graphene.Boolean()
    date = graphene.DateTime()

    def resolve_description(self, info, **kwargs):
        return self.description

    def resolve_autovouch(self, info, **kwargs):
        return self.autovouch

    def resolve_date(self, info, **kwargs):
        return self.date

    def resolve_voucher(self, info, **kwargs):
        if self.voucher:
            return retrieve_v2_profile(info.context, self.voucher.auth0_user_id)
        return None


class Profile(graphene.ObjectType, AbstractProfile):
    """V2 Schema Profile object for Graphene."""

    # Non v2 profile fields
    manager = graphene.Field(RelatedProfile)
    directs = graphene.List(RelatedProfile)
    vouches = graphene.List(Vouches)

    class Meta:
        default_resolver = dino_park_resolver
