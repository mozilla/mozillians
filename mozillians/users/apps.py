from django.apps import AppConfig


class UserConfig(AppConfig):
    name = 'mozillians.users'
    label = 'users'

    def ready(self):
        import mozillians.users.signals # noqa
