import autocomplete_light

from mozillians.groups.models import Group


class GroupAutocomplete(autocomplete_light.AutocompleteModelBase):
    search_fields = ['name', 'url', 'description', 'irc_channel', 'aliases__name']
    choices = Group.objects.all()


autocomplete_light.register(Group, GroupAutocomplete,
                            name='Groups')
