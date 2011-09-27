from jingo import register


@register.filter
def vouched(user):
    if hasattr(user, 'is_vouched'):
        return user.is_vouched()
