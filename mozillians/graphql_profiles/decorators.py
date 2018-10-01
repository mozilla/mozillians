def graphql_permission_check(func):
    """Decorator to check if a user has the permissions to edit a profile."""
    def mutation_wrapper(cls, root, info, user_id, basic_profile_data):
        user = info.context.user
        msg = ''

        # Do not allow anonymous users to edit profiles
        if not user.is_authenticated():
            msg = 'You need to be authenticated to edit a profile.'

        # Allow edits only to the owner of the profile
        if not user.userprofile.auth0_user_id or user_id != user.userprofile.auth0_user_id:
            msg = 'You can edit only your own profile.'

        if msg:
            if hasattr(cls, 'errors'):
                return cls(errors=[msg])
            raise Exception(msg)

        return func(cls, root, info, user_id, basic_profile_data)
    return mutation_wrapper
