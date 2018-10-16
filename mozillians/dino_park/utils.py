class UserAccessLevel(object):
    """Class to handle privacy related scopes in DinoPark."""
    # Privacy classifications for Dino Park
    PRIVATE = 'private'
    STAFF = 'staff'
    NDA = 'nda'
    VOUCHED = 'vouched'
    AUTHENTICATED = 'authenticated'
    PUBLIC = 'public'

    @classmethod
    def get_privacy(cls, request, user=None):
        """Return user privacy clearance for Dino Park."""
        request_user = request.user

        if request_user.is_authenticated():
            # The order here is important. Private has the highest access of all and
            # public the least.
            # Admins (superusers) have PRIVATE access. This is matching functionality from
            # current mozillians.org
            if (request_user.is_superuser or (user and user == request_user)):
                return cls.PRIVATE
            # TODO: This needs to change to hris assertion from ES
            if request_user.userprofile.groups.filter(name='staff').exists():
                return cls.STAFF
            if request_user.userprofile.is_nda:
                return cls.NDA
            if request_user.userprofile.is_vouched:
                return cls.VOUCHED
            # If we did not match all the above cases, return an authenticated user
            return cls.AUTHENTICATED
        return cls.PUBLIC
