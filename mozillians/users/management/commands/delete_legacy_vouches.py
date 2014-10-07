from optparse import make_option

from django.core.management.base import BaseCommand

from mozillians.users.models import Vouch


class Command(BaseCommand):
    option_list = list(BaseCommand.option_list) + [
        make_option('--dry-run',
                    dest='dry-run',
                    action='store_true',
                    default=False,
                    help='Run without changing the DB.')
    ]

    def handle(self, *args, **options):
        dry_run = options.get('dry-run')
        legacy_vouches = Vouch.objects.filter(description='')

        if dry_run:
            msg = "%d legacy vouches to be deleted." % legacy_vouches.count()
            self.stdout.write(msg)
        else:
            legacy_vouches.delete()
            msg = "%d legacy vouches left." % legacy_vouches.count()
            self.stdout.write(msg)
