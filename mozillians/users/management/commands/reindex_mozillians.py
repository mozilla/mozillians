from django.core.management.base import BaseCommand

from mozillians.users.tasks import index_all_profiles


class Command(BaseCommand):
    def handle(self, *args, **options):
        index_all_profiles()
