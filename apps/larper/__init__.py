"""
LARPER - Let's Authenticate Resources Per Each Request

Design
======

larper provides the following ways to start an LDAP directory session:
* UserSession.connect(request)
* RegistrarSession.connect(request)
* AdminSession.connect(request)

UserSession
-----------

Once one has obtained a directory session, one can search or
update a person in the phonebook.

Search results are larper.Person objects.

People have larper.SystemId objects as well as profile photos.

RegistararSession
-----------------

With a registrar session, one can add new users to the system.

AdminSession
------------

With an admin session, one can delete users from the system.
"""
import hashlib
import os
import re
from time import time

import ldap
from ldap.dn import explode_dn, escape_dn_chars
from ldap.filter import filter_format
from ldap.modlist import addModlist, modifyModlist

from django.conf import settings
from django.core import signing
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.db.models import Q

import commonware.log
from funfactory.utils import absolutify
from statsd import statsd
from users.models import UserProfile

import browserid

log = commonware.log.getLogger('m.larper')


ASSERTION_SIGNED_KEY = 'ASSERTION'
ASSERTION_KEY = 'assertion'


def get_assertion(request):
    """Retrieves the assertion from the user's session."""
    d = request.session.get(ASSERTION_SIGNED_KEY)
    if d:
        assertion = signing.loads(d).get(ASSERTION_KEY)
        return (hashlib.md5(assertion).hexdigest(), assertion)
    else:
        return (None, None)


def store_assertion(request, assertion):
    """Stores assertion into the session.

    request - Django web request
    password - A clear text password
    """
    request.session[ASSERTION_SIGNED_KEY] = signing.dumps({
            ASSERTION_KEY: assertion})


class NO_SUCH_PERSON(Exception):
    """Raised when a search by unique_id fails."""
    pass


class INCONCEIVABLE(Exception):
    """Raised when something that should not happen,
    happens. If this happens often, this Exception
    might not mean what you think it means."""
    pass


CONNECTIONS_KEY = 'larper_conns'

READ = 0
WRITE = 1

MOZILLA_IRC_SERVICE_URI = 'irc://irc.mozilla.org/'
KNOWN_SERVICE_URIS = [
    MOZILLA_IRC_SERVICE_URI,
]

KNOWN_USER = re.compile(
    'dn:uniqueIdentifier=([^,]*),ou=people,dc=mozillians,dc=org')
NEW_USER = re.compile('dn:uid=([^,]*),cn=browser-id,cn=auth')
PEEP_SRCH_FLTR = '(&(objectClass=mozilliansPerson)(|(cn=*%s*)(mail=*%s*)))'
IRC_SRCH_FLTR = """(&(objectClass=mozilliansLink)(mozilliansServiceID=*%s*)
                     (mozilliansServiceURI=irc://irc.mozilla.org/))"""
NONVOUCHED_SRCH_FLTR = """(&(objectClass=mozilliansPerson)(|(cn=*%s*)
                            (mail=*%s*))(&(!(mail=*@mozilla*))
                            (!(mozilliansVouchedBy=*))))"""
NONVOUCHED_EMAIL_SRCH_FLTR = """(&(|(mail=*%s*)(uid=*%s*))
                                    (&(!(mail=*@mozilla*))
                                    (!(mozilliansVouchedBy=*))))"""


class UserSession(object):
    """
    A directory session for the currenly logged in user.

    Data access to the directory is mediated on a
    user by user, request by request basis. A person object
    may be missing, or search results may be empty if the
    current viewer of a directory doesn't have permissions
    to see certain people.
    """
    def __init__(self, request):
        self.request = request
        self._is_bound = False

    def _ensure_conn(self, mode):
        """Lazily connect to LDAP.

        mode - One of READ or WRITE. Pass WRITE
        if any of the LDAP operations will include
        adding, modifying, or deleting entires.

        UserSession connections will be established with
        an assertion stored in the user's session.

        Raises exceptions if this class is used with a
        non-authenticated user (Anonymous).
        """
        return self._ensure_conn_sasl(mode)

    def _ensure_conn_sasl(self, mode):
        """Lazily connect to LDAP using sasl bind.

        Using the assertion from the user's session,
        connects to LDAP via sasl_interactive_bind and
        the BROWSER-ID auth mechanism.
        """
        assrtn_hsh, assertion = get_assertion(self.request)
        if not assertion:
            raise Exception('Programming error, do not use UserSession '
                            'without an assertion')

        if not hasattr(self.request, CONNECTIONS_KEY):
            self.request.larper_conns = [{}, {}]

        fresh_bind = False
        if assrtn_hsh not in self.request.larper_conns[mode]:
            if mode == WRITE:
                server_uri = settings.LDAP_SYNC_PROVIDER_URI
            else:
                server_uri = settings.LDAP_SYNC_CONSUMER_URI
            self.conn = ldap.initialize(server_uri)
            self.request.larper_conns[mode][assrtn_hsh] = self.conn
            self._sasl_bind(assertion)
            fresh_bind = True
        else:
            self.conn = self.request.larper_conns[mode][assrtn_hsh]

        # During registration, during a single request, we can go from
        # an invalid dn, to a valid one. We'll need to re-bind to LDAP.
        if not fresh_bind and not self._dn(assertion):
            self._sasl_bind(assertion)
        return self.conn

    def _ensure_conn_simple(self, mode):
        """Lazily connect to LDAP using bind.

        Using the dn and password from the apps config
        connects to LDAP via simple bind. Useful for
        non-human agents.
        """
        dn, password = self.dn_pass()
        if not hasattr(self.request, CONNECTIONS_KEY):
            self.request.larper_conns = [{}, {}]
        if dn not in self.request.larper_conns[mode]:
            if mode == WRITE:
                server_uri = settings.LDAP_SYNC_PROVIDER_URI
            else:
                server_uri = settings.LDAP_SYNC_CONSUMER_URI
            self.conn = ldap.initialize(server_uri)
            self.request.larper_conns[mode][dn] = self.conn
            self.conn.bind_s(dn, password)
        return self.request.larper_conns[mode][dn]

    def _sasl_bind(self, assertion):
        """Binds to LDAP using sasl and BrowserID credentials."""
        audience = absolutify('')
        sasl_creds = browserid.Credentials(assertion, audience)
        self.conn.sasl_interactive_bind_s('', sasl_creds)

    def _dn(self, assertion):
        """Convience wrapper for checking dn after sasl bind."""
        dn = None
        new_dn = self.conn.whoami_s()
        # this could be an invalid dn if the user isn't registered
        # it would look like uid=shout@ozten.com,cn=browser-id,cn=auth
        match = KNOWN_USER.match(new_dn)
        if match:
            dn = Person.dn(match.group(1))
            statsd.incr('larper.existing_email_address')
            log.info('New DN=%s' % dn)
        else:
            statsd.incr('larper.unknown_email_address')
            log.info('Unknown email address %s' % new_dn)
        return dn

    def dn_pass(self):
        """Abstract method for managing dn and password in sub-classes.

        Returns a tuple of LDAP distinguished name and password
        for use during authentication.
        Subclasses of UserSession should override this method
        if they don't auth against the user in the session.
        """
        raise Exception('UserSession should be used with an assertion, '
                        'not dn/password')

    def registered_user(self):
        """Checks if the current user is registered in the system.

        Returns a two element tuple:

        * boolean - True if the user is registered, False if they are
                    new.
        * string -  unique_id if they are registered, verified
                    email address if they are new.
        """
        conn = self._ensure_conn(READ)
        dn = conn.whoami_s()
        match = KNOWN_USER.match(dn)
        if match:
            return (True, match.group(1))
        else:
            match = NEW_USER.match(dn)
            if match:
                return (False, match.group(1))
            else:
                raise INCONCEIVABLE('LDAP authz error for dn=[%s]' % dn)

    def search(self, query, nonvouched_only=False):
        """
        General purpose 'quick' search. Returns a list of
        larper.Person objects.
        """
        encoded_q = query.encode('utf-8')
        if nonvouched_only:
            peep_esc_q = filter_format(NONVOUCHED_SRCH_FLTR, (encoded_q, encoded_q))
        else:
            peep_esc_q = filter_format(PEEP_SRCH_FLTR, (encoded_q, encoded_q))
        irc_esc_q = filter_format(IRC_SRCH_FLTR, (encoded_q,))
        people = self._people_search(peep_esc_q)
        irc_nicks = self._irc_search(irc_esc_q)
        people += self._people_from_irc_results_search(irc_nicks)
        return self._populate_people_results(people)

    def search_by_name(self, query):
        """Searches against the full_name field for people.

        Returns same type of data as search.
        """
        q = filter_format("(cn=*%s*)", (query.encode('utf-8'),))
        return self._populate_people_results(self._people_search(q))

    def search_by_email(self, query, nonvouched_only=False):
        """
        Searches against the email fields for people. Returns
        same type of data as search.
        """
        encoded_q = query.encode('utf-8')
        if nonvouched_only:
            q = filter_format(NONVOUCHED_EMAIL_SRCH_FLTR,
                              (encoded_q, encoded_q,))
        else:
            q = filter_format("(|(mail=*%s*)(uid=*%s*))",
                              (encoded_q, encoded_q,))
        return self._populate_people_results(self._people_search(q))

    def get_by_unique_id(self, unique_id, use_master=False):
        """Retrieves a person from LDAP with this unique_id.

        Raises NO_SUCH_PERSON if unable to find them.

        use_master can be set to True to force reading from master
        where stale data isn't acceptable.
        """
        f = "(&(objectClass=mozilliansPerson)(uniqueIdentifier=%s))"
        q = filter_format(f, (unique_id,))
        results = self._people_search(q, use_master)
        msg = 'Unable to locate %s in the LDAP directory'
        if not results:
            raise NO_SUCH_PERSON(msg % unique_id)
        elif len(results) == 1:
            _dn, attrs = results[0]
            # Pending users will detect the existance of another
            # person, but there won't be any data besides uniqueIdentifier
            if 'sn' not in attrs:
                raise NO_SUCH_PERSON(msg % unique_id)
            else:
                return Person.new_from_directory(attrs)
        else:
            msg = 'Multiple people found for %s. This should never happen.'
            statsd.incr('larper.errors.get_by_unique_id_has_multiple')
            raise INCONCEIVABLE(msg % unique_id)

    def profile_photo(self, unique_id, use_master=False):
        """Retrieves a person's profile photo.

        Returns jpeg binary data.
        """
        attrs = self._profile_photo_attrs(unique_id, use_master)
        if 'jpegPhoto' in attrs:
            return attrs['jpegPhoto'][0]
        return False

    def profile_service_ids(self, person_unique_id, use_master=False):
        """Returns a dict that contains remote system ids.

        Keys for dict include:

        * MOZILLA_IRC_SERVICE_URI

        Values are a SystemId object for that service.

        use_master can be set to True to force reading from master
        where stale data isn't acceptable.
        """
        services = {}
        if use_master:
            conn = self._ensure_conn(WRITE)
        else:
            conn = self._ensure_conn(READ)
        search_filter = '(mozilliansServiceURI=*)'
        rs = conn.search_s(Person.dn(person_unique_id),
                           ldap.SCOPE_SUBTREE,
                           search_filter)
        for r in rs:
            _dn, attrs = r
            sysid = SystemId(person_unique_id,
                             attrs['uniqueIdentifier'][0].decode('utf-8'),
                             attrs['mozilliansServiceURI'][0].decode('utf-8'),
                             service_id=attrs['mozilliansServiceID'][0]\
                                 .decode('utf-8'))
            services[attrs['mozilliansServiceURI'][0]] = sysid
        return services

    def _profile_photo_attrs(self, unique_id, use_master=False):
        """Returns dict that contains the jpegPhoto key or None."""
        if use_master:
            conn = self._ensure_conn(WRITE)
        else:
            conn = self._ensure_conn(READ)
        search_filter = filter_format("(uniqueIdentifier=%s)", (unique_id,))
        rs = conn.search_s(settings.LDAP_USERS_GROUP, ldap.SCOPE_SUBTREE,
                             search_filter, ['jpegPhoto'])
        for r in rs:
            _dn, attrs = r
            if 'jpegPhoto' in attrs:
                return attrs
        return {}

    def update_person(self, unique_id, form):
        """Updates a person's LDAP directory record based on ProfileForm.

        Method always uses master.
        """
        conn = self._ensure_conn(WRITE)

        dn = Person.dn(unique_id)

        person = self.get_by_unique_id(unique_id)
        form['unique_id'] = person.unique_id

        if 'email' not in form:
            form['email'] = person.username

        newp = Person.form_to_profile_attrs(form)
        modlist = modifyModlist(person.ldap_attrs(), newp,
                                ignore_oldexistent=1)
        if modlist:
            conn.modify_s(dn, modlist)

        services = self.profile_service_ids(unique_id)
        oldservs = dict((k, v.ldap_attrs()) for k, v in services.iteritems())
        newservs = SystemId.form_to_service_ids_attrs(form)
        for service_uri in KNOWN_SERVICE_URIS:
            newserv = newservs[service_uri]

            if service_uri in oldservs:
                oldserv = oldservs[service_uri]
                newserv['uniqueIdentifier'][0] = oldserv['uniqueIdentifier'][0]
                sys_id_dn = SystemId.dn(unique_id,
                                        oldserv['uniqueIdentifier'][0])

                if newserv['mozilliansServiceID'][0]:
                    modlist = modifyModlist(oldserv, newserv)
                    if modlist:
                        conn.modify_s(sys_id_dn, modlist)
                else:
                    conn.delete_s(sys_id_dn)
            else:
                sys_id_dn = SystemId.dn(unique_id,
                                        newserv['uniqueIdentifier'][0])
                if newserv['mozilliansServiceID'][0]:
                    modlist = addModlist(newserv)
                    if modlist:
                        conn.add_s(sys_id_dn, modlist)
        return True

    def update_profile_photo(self, unique_id, form):
        """Adds or Updates a person's profile photo.

        unique_id
        form - An instance of phonebook.forms.ProfileForm
        Safe to call if no photo has been uploaded by the user.

        Method always uses master.
        """
        if 'photo' in form and form['photo']:
            photo = form['photo'].file.read()
        elif form.get('photo_delete'):
            photo = None
        else:
            return False

        conn = self._ensure_conn(WRITE)
        dn = Person.dn(unique_id)

        attrs = self._profile_photo_attrs(unique_id)
        if photo:
            new_attrs = dict(jpegPhoto=photo)
        elif attrs.get('jpegPhoto'):
            new_attrs = dict(**attrs)
            del new_attrs['jpegPhoto']
        else: # If no photo exists for this user, we don't bother trying to
              # delete it.
            return False

        # Person record will always exist, so we only do a mod
        modlist = modifyModlist(attrs, new_attrs,
                                ignore_oldexistent=bool(photo))

        if modlist:
            conn.modify_s(dn, modlist)

    def _people_search(self, search_filter, use_master=False):
        """Wrapper function around LDAP search.

        use_master can be set to True to force reading from master
        where stale data isn't acceptable.
        """
        if use_master:
            conn = self._ensure_conn(WRITE)
        else:
            conn = self._ensure_conn(READ)
        return conn.search_s(settings.LDAP_USERS_GROUP, ldap.SCOPE_ONELEVEL,
                             search_filter, Person.search_attrs)

    def _irc_search(self, search_filter, use_master=False):
        """Searches for SystemIDs based on IRC nickname.

        use_master can be set to True to force reading from master
        where stale data isn't acceptable.
        """
        if use_master:
            conn = self._ensure_conn(WRITE)
        else:
            conn = self._ensure_conn(READ)
        return conn.search_s(settings.LDAP_USERS_GROUP, ldap.SCOPE_SUBTREE,
                             search_filter, SystemId.search_attrs)

    def _people_from_irc_results_search(self, irc_results, use_master=False):
        """Searches for SystemIDs based on IRC nickname.

        use_master can be set to True to force reading from master
        where stale data isn't acceptable.
        """
        if use_master:
            conn = self._ensure_conn(WRITE)
        else:
            conn = self._ensure_conn(READ)
        uniq_ids = []
        for result in irc_results:
            dn, attrs = result

            parts = ldap.dn.explode_dn(dn)
            # ['uniqueIdentifier=13173391.34', 'uniqueIdentifier=7f3a67u000',
            #  'ou=people', 'dc=mozillians', 'dc=org']
            if len(parts) > 1:
                subparts = parts[1].split('=')
            # ['uniqueIdentifier', '7f3a67u000001']
            if len(subparts) == 2:
                # 7f3a67u000001
                uniq_ids.append(subparts[1])
        if not uniq_ids:
            return []

        # "(uniqueIdentifier=7f3a67u00001)(uniqueIdentifier=7f3a67u00002)"
        frags = ["(uniqueIdentifier=%s)" % x for x in uniq_ids]
        dn_filter_frag = ''.join(frags)

        base_filter = '(&(objectClass=mozilliansPerson)(|%s))'
        search_filter = base_filter % dn_filter_frag
        return conn.search_s(settings.LDAP_USERS_GROUP, ldap.SCOPE_SUBTREE,
                             search_filter, Person.search_attrs)

    def _populate_people_results(self, results):
        """Processes search results.

        Given LDAP search results, method sorts and ensures unique
        set of results.
        """
        people = []
        cache = {}
        for result in results:
            dn, attrs = result
            if 'sn' not in attrs:
                continue
            p = Person.new_from_directory(attrs)
            if not p or p.unique_id in cache:
                continue
            else:
                cache[p.unique_id] = True
                people.append(p)
        return people

    def __unicode__(self):
        """Provides a string representation for this object."""
        return u'<larper.UserSession for %s>' % self.request.user.username

    @staticmethod
    def connect(request):
        """Open (or reuse) a connection to the phonebook directory.

        Request must contain an authenticated user.
        Data requests will be authorized based on the current
        users rights.

        Connection pooling, master/slave routing, and other low
        level details will automagically work.
        """
        return UserSession(request)

    @staticmethod
    def disconnect(request):
        """Disconnects from LDAP.

        Releases all connections to the LDAP directory, including:
        * UserSession instances
        * AdminSession instances
        * RegistrarSession instances
        """
        if hasattr(request, CONNECTIONS_KEY):
            # Each mode (read/write)
            conns = request.larper_conns
            for i in range(len(conns)):
                for dn in conns[i].keys():
                    conns[i][dn].unbind()
                    del request.larper_conns[i][dn]


class Person(object):
    """
    A person has a couple required attributes and then lots of optional
    profile details. Data is populated based on what the current request's
    user should see. If a property is None, it may be because
    * the profile's property doesn't have any data or
    * the viewer doesn't have permission to see this property

    Required Properties
    -------------------

    * unique_id - A stable id that is randomly generated
    * username - Email address used for authentication
    * full_name - A person's full name
    * last_name - A person's last name

    Optional Properties
    -------------------

    * first_name - A person's first name
    * biography - A person's bio
    * voucher_unique_id - The unique_id of the Mozillian who vouched for them.

    Photo
    -----
    Photo access is done seperatly to improve data access performance.

    For a user's photo, see larper.UserSession.profile_photo and
    update_profile_photo.
    """
    required_attrs = ['uniqueIdentifier', 'uid', 'cn', 'sn']
    optional_attrs = ['givenName', 'description', 'mail', 'telephoneNumber',
             'mozilliansVouchedBy']
    search_attrs = required_attrs + optional_attrs
    binary_attrs = ['jpegPhoto']

    def __init__(self, unique_id, username,
                 first_name=None, last_name=None,
                 full_name=None,
                 biography=None,
                 voucher_unique_id=None):
        self.unique_id = unique_id
        self.username = username

        self.first_name = first_name
        self.last_name = last_name
        self.full_name = full_name
        self.display_name = '%s %s' % (first_name, last_name)
        self.biography = biography
        self.voucher_unique_id = voucher_unique_id

    def __unicode__(self):
        """Provides a string representation for this object."""
        return u'%s %s' % (self.first_name, self.last_name)

    @staticmethod
    def new_from_directory(ldap_attrs):
        """Creates Person objects based on LDAP attributes.

        Given a dictionary of LDAP search result attributes, this
        method returns a larper.Person instance.
        """
        # givenName is optional in LDAP, but required by our API
        given_name = ldap_attrs.get('givenName', [''])
        p = Person(ldap_attrs['uniqueIdentifier'][0].decode('utf-8'),
                   ldap_attrs['uid'][0].decode('utf-8'),
                   given_name[0].decode('utf-8'),
                   ldap_attrs['sn'][0].decode('utf-8'),
                   ldap_attrs['cn'][0].decode('utf-8'))

        if 'description' in ldap_attrs:
            p.biography = ldap_attrs['description'][0].decode('utf-8')

        if 'mozilliansVouchedBy' in ldap_attrs:
            voucher = ldap_attrs['mozilliansVouchedBy'][0].decode('utf-8')
            p.voucher_unique_id = Person.unique_id(voucher)

        return p

    def get_profile(self):
        """Retrieve the Django UserProfile for this Person.

        This is full of hacks because all the Mozillians servers are throwing
        ObjectDoesNotExist errors (even in production) if we try a straight-up
        `User.objects.get(email=self.username)`. This method now exhaustively
        tries to get a User object from the database. If it doesn't find one,
        or finds one without a UserProfile, we make one on the spot, trying
        our best to fill things in sanely. FML.

        See: https://bugzilla.mozilla.org/show_bug.cgi?id=698699

        TODO: Remove this as soon as possible. It's insane.
        """
        user = (User.objects.filter(Q(email=self.username) |
                                    Q(username=self.username)))[:1]

        if user:
            # Yes, sometimes the User exists but the UserProfile doesn't.
            # See: https://bugzilla.mozilla.org/show_bug.cgi?id=699234
            try:
                profile = user[0].get_profile()
            except ObjectDoesNotExist, e:
                statsd.incr('user.errors.profile_doesnotexist')
                log.warning(e)

                profile = UserProfile.objects.create(user=user[0])
        else:
            statsd.incr('user.errors.doesnotexist')
            log.warning('No user with email %s' % self.username)

            user = User(username=self.username, email=self.username)
            user.set_unusable_password()
            user.save()

            profile = user.get_profile()

        return profile

    def ldap_attrs(self):
        """Transforms Person object into LDAP compatible data.

        Converts this person object into a dict compatible
        with the low level ldap libraries.
        """
        objectclass = ['inetOrgPerson', 'person', 'mozilliansPerson']
        full_name = u'%s %s' % (self.first_name, self.last_name)
        full_name = full_name
        attrs = dict(objectclass=objectclass,
                     uniqueIdentifier=[self.unique_id],
                     uid=[self.username],
                     sn=[self.last_name],
                     cn=[full_name],
                     displayName=[full_name],
                     mail=[self.username])

        # Optional
        if self.first_name:
            attrs['givenName'] = [self.first_name]
        if self.biography:
            attrs['description'] = [self.biography]

        # TODO - deal with this somewhere else?
        if self.voucher_unique_id:
            attrs['mozilliansVouchedBy'] = [Person.dn(self.voucher_unique_id)]
        return attrs

    @staticmethod
    def form_to_profile_attrs(form):
        """Transforms a form into LDAP compatible data.

        Creates a profile dict compatible with the low level ldap libraries
        from a form dictionary.

        Form must contain the following keys:
        * unique_id
        * username
        * first_name
        * last_name
        """
        objectclass = ['inetOrgPerson', 'person', 'mozilliansPerson']
        full_name = u'%s %s' % (form['first_name'], form['last_name'])
        full_name = full_name.encode('utf-8')
        attrs = dict(objectclass=objectclass,
                     uniqueIdentifier=[form['unique_id'].encode('utf-8')],
                     uid=[form['email'].encode('utf-8')],

                     sn=[form['last_name'].encode('utf-8')],
                     cn=[full_name],
                     displayName=[full_name],
                     mail=[form['email'].encode('utf-8')])

        if 'password' in form:
            attrs['userPassword'] = [form['password'].encode('utf-8')]

        if 'first_name' in form and form['first_name']:
            attrs['givenName'] = [form['first_name'].encode('utf-8')]
        else:
            attrs['givenName'] = [None]

        if 'biography' in form and form['biography']:
            attrs['description'] = [form['biography'].encode('utf-8')]
        else:
            attrs['description'] = [None]

        return attrs

    @staticmethod
    def unique_id(dn):
        """Parses DN into a unique_id."""
        dn_parts = explode_dn(dn)
        reg = re.compile('uniqueIdentifier=(.*)', re.IGNORECASE)
        for part in dn_parts:
            matcher = reg.match(part)
            if matcher:
                return matcher.groups()[0]
        raise INVALID_PERSON_DN(dn)

    @staticmethod
    def dn(unique_id):
        """Formats a unique_id into a DN."""
        params = (escape_dn_chars(unique_id), settings.LDAP_USERS_GROUP)
        return 'uniqueIdentifier=%s,%s' % params


class SystemId(object):
    """
    Represents a connection between a person and
    a remote system.

    Required Properties
    -------------------

    * person_unique_id - Person who owns this system id
    * unique_id - internal stable id for this service id
    * service_uri - A URI which commonly identifies a remote system
    * service_id - username, email, or whatever is used in the
               remote system as an ID.

    KISS: Although many URIs could signify a remote system, we should not
    have several URIs for a service which would only have one auth
    credentials. Example: G+, Google docs, and Gmail would only have one
    URI - http://google.com. Youtube (a Google property) would have
    it's own URI, since it has seperate username.
    """
    search_attrs = ['uniqueIdentifier', 'mozilliansServiceURI',
                    'mozilliansServiceID']

    def __init__(self, person_unique_id, unique_id, service_uri, service_id):
        self.person_unique_id = person_unique_id
        self.unique_id = unique_id
        self.service_uri = service_uri
        self.service_id = service_id

    def ldap_attrs(self):
        """Transforms SystemId objects into LDAP compatible data.

        Converts this SystemId object into a dict compatible
        with the low level ldap libraries.
        """
        attrs = dict(objectclass=['mozilliansLink'],
                     uniqueIdentifier=[self.unique_id],
                     mozilliansServiceURI=[self.service_uri],
                     mozilliansServiceID=[self.service_id])
        return attrs

    @staticmethod
    def form_to_service_ids_attrs(form):
        """Creates a list of dicts.

        Each dict of remote system ids
        is compatible with the low level ldap libraries from
        a form dictionary.

        See phonebook.forms.ProfileForm for full list of fields.
        """
        known_service_fields = [
            ('irc_nickname', MOZILLA_IRC_SERVICE_URI),
        ]
        attrs_list = {}
        for field, uri in known_service_fields:
            system_id = form[field].encode('utf-8')

            system_unique_id = form['%s_unique_id' % field].encode('utf-8')
            if not system_unique_id:
                system_unique_id = str(time())
            if not system_id:
                system_id = None
            attrs = dict(objectclass=['mozilliansLink'],
                         uniqueIdentifier=[system_unique_id],
                         mozilliansServiceURI=[MOZILLA_IRC_SERVICE_URI],
                         mozilliansServiceID=[system_id])
            attrs_list[uri] = attrs
        return attrs_list

    @staticmethod
    def dn(person_unique_id, unique_id):
        """Formats an LDAP distinguished name for a remote system id."""
        params = (escape_dn_chars(unique_id), Person.dn(person_unique_id))
        return 'uniqueIdentifier=%s,%s' % params


class INVALID_PERSON_DN(Exception):
    """A function which expected a valid DN was
    given an invalid DN. Probably didn't contain a
    uniqueIdentifier component."""
    pass


# Increase length of random uniqueIdentifiers as size of Mozillians
# community enters the low millions ;)
UUID_SIZE = 5


class RegistrarSession(UserSession):
    """
    A directory session for the registrar user.
    """
    def _ensure_conn(self, mode):
        """Overrides UserSession._ensure_conn to use dn pass.

        RegistrarSession uses a configurable dn and password
        instead of a BrowserID assertion.
        """
        return self._ensure_conn_simple(mode)

    def dn_pass(self):
        """Returns registrar dn and password."""
        return (settings.LDAP_REGISTRAR_DN, settings.LDAP_REGISTRAR_PASSWORD)

    def create_person(self, form):
        """Creates a new user account in the LDAP directory.

        form - An instance of phonebook.forms.RegistrationForm
        returns a string which is the unique_id of the new user.

        Method always uses master.
        """
        conn = self._ensure_conn(WRITE)
        unique_id = os.urandom(UUID_SIZE).encode('hex')
        form['unique_id'] = unique_id
        new_dn = Person.dn(unique_id)

        attrs = Person.form_to_profile_attrs(form)
        mods = addModlist(attrs)
        conn.add_s(new_dn, mods)
        return unique_id

    @staticmethod
    def connect(request):
        """Open (or reuse) a connection to the phonebook directory.

        Data requests will be authorized based on the shared
        system's registrar account.

        Connection pooling, master/slave routing, and other low
        level details will automagically work.
        """
        return RegistrarSession(request)


class AdminSession(UserSession):
    """A directory session for the admin user."""

    def _ensure_conn(self, mode):
        """Overrides UserSession._ensure_conn to use dn and pass.

        Admin session uses a configurable dn and password
        instead of a BrowserID assertion.
        """
        return self._ensure_conn_simple(mode)

    def dn_pass(self):
        """Returns administrator dn and password."""
        return (settings.LDAP_ADMIN_DN, settings.LDAP_ADMIN_PASSWORD)

    def delete_person(self, unique_id):
        """Completely removes a user's data from the LDAP directory.

        Note: Does not un-vouch any Mozillians for whom this user
        has vouched.

        Method always uses master.
        """
        conn = self._ensure_conn(WRITE)
        person_dn = Person.dn(unique_id)

        # Kill SystemId or other children
        rs = conn.search_s(Person.dn(unique_id),
                           ldap.SCOPE_ONELEVEL,
                           '(objectclass=*)')
        for sub_dn, attrs in rs:
            conn.delete_s(sub_dn)

        conn.delete_s(person_dn)
        return self

    @staticmethod
    def connect(request):
        """Open (or reuse) a connection to the phonebook directory.

        Data requests will be authorized based on the shared
        system's admin account.

        Connection pooling, master/slave routing, and other low
        level details will automagically work.
        """
        return AdminSession(request)


def change_password(unique_id, oldpass, password):
    """Changes a user's password."""
    dn = Person.dn(unique_id)

    conn = ldap.initialize(settings.LDAP_SYNC_PROVIDER_URI)
    try:
        conn.bind_s(dn, oldpass)

        conn.passwd_s(dn, None, password)
        log.debug("Changed %s password" % dn)
        return True
    except Exception, e:
        log.error("Password change failed %s", e)
        return False
    finally:
        conn.unbind()


def set_password(username, password):
    """Resets a user's LDAP password.

    .. warning:
    *Careful!* This function has the capability to change
    anyone's password. It should only be used for
    un-authenticated users from the reset-password email
    flow.

    *If the user is authenticated*, then
    *use the change_password method above*.
    """
    conn = ldap.initialize(settings.LDAP_SYNC_PROVIDER_URI)
    try:
        conn.bind_s(settings.LDAP_ADMIN_DN,
                    settings.LDAP_ADMIN_PASSWORD)
        search_filter = filter_format("(uid=%s)", (username,))
        rs = conn.search_s(settings.LDAP_USERS_GROUP, ldap.SCOPE_SUBTREE,
                           search_filter)
        for dn, attrs in rs:
            conn.passwd_s(dn, None, password)
            log.info("Resetting %s password" % dn)
    finally:
        conn.unbind()


def _return_all():
    """Return all LDAP records, provided no LIMITs are set."""
    conn = ldap.initialize(settings.LDAP_SYNC_PROVIDER_URI)
    conn.bind_s(settings.LDAP_ADMIN_DN, settings.LDAP_ADMIN_PASSWORD)
    encoded_q = '@'.encode('utf-8')
    search_filter = filter_format('(|(mail=*%s*)(uid=*%s*))',
                                  (encoded_q, encoded_q,))

    rs = conn.search_s(settings.LDAP_USERS_GROUP, ldap.SCOPE_SUBTREE,
                       search_filter)
    return rs


def get_user_by_email(email):
    """Given an email address, return an ldap record."""

    conn = ldap.initialize(settings.LDAP_SYNC_PROVIDER_URI)
    conn.bind_s(settings.LDAP_ADMIN_DN, settings.LDAP_ADMIN_PASSWORD)
    encoded_q = email.encode('utf-8')
    search_filter = filter_format('(|(mail=*%s*)(uid=*%s*))',
                                  (encoded_q, encoded_q,))
    rs = conn.search_s(settings.LDAP_USERS_GROUP, ldap.SCOPE_SUBTREE,
                       search_filter)
    if rs:
        return rs[0]


def get_user_by_uid(uid):
    """Given a uniqueIdentifier, return an ldap record."""
    conn = ldap.initialize(settings.LDAP_SYNC_PROVIDER_URI)
    conn.bind_s(settings.LDAP_ADMIN_DN, settings.LDAP_ADMIN_PASSWORD)
    search_filter = filter_format('(uniqueIdentifier=%s)', (uid,))

    rs = conn.search_s(settings.LDAP_USERS_GROUP, ldap.SCOPE_SUBTREE,
                       search_filter, Person.search_attrs)
    if rs:
        return rs[0]


def record_vouch(voucher, vouchee):
    """Updates a *Pending* account to *Mozillian* status.

    voucher - The unique_id of the Mozillian who will vouch
    vouchee - The unique_id of the Pending user who is being vouched for
    """
    conn = ldap.initialize(settings.LDAP_SYNC_PROVIDER_URI)
    conn.bind_s(settings.LDAP_ADMIN_DN, settings.LDAP_ADMIN_PASSWORD)
    voucher_dn = Person.dn(voucher)
    vouchee_dn = Person.dn(vouchee)

    modlist = [(ldap.MOD_ADD, 'mozilliansVouchedBy', [voucher_dn])]
    conn.modify_s(vouchee_dn, modlist)
    return True
