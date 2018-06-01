from django.apps import AppConfig

from mozillians.common.auth0 import MozilliansAuthZeroManagement


default_app_config = 'mozillians.phonebook.PhonebookConfig'

AuthZeroManagementApi = MozilliansAuthZeroManagement()


class PhonebookConfig(AppConfig):
    name = 'mozillians.phonebook'
