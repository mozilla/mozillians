from django.apps import AppConfig


class CommonConfig(AppConfig):
    name = 'mozillians.common'
    label = 'common'

    def ready(self):
        import mozillians.common.signals # noqa
