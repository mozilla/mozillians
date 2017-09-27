from django.apps import AppConfig


CIS_GROUPS = [
    'cis_whitelist',
    'nda'
]


default_app_config = 'mozillians.groups.GroupConfig'


class GroupConfig(AppConfig):
    name = 'mozillians.groups'
