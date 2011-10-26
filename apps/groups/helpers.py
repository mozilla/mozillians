from jingo import register


@register.function
def stringify_groups(groups, omit_system=True):
    """Change a list of Group objects into a space-delimited string."""
    if omit_system:
        groups = (g for g in groups if not g._is_system())

    return u' '.join([group.name for group in groups])
