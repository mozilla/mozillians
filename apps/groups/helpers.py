from jingo import register


@register.function
def stringify_groups(groups):
    """Change a list of Group objects into a space-delimited string."""
    return u','.join([group.name for group in groups])
