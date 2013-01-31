def merge_groups(master_group, group_list):
    """Merge group_list into master_group."""
    for group in group_list:
        map(lambda x: master_group.userprofile_set.add(x),
            group.userprofile_set.values_list('id', flat=True))
        group.aliases.update(alias=master_group)
        group.delete()
