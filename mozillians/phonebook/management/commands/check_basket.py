"""
Check whether Basket is accessible and working.
If everything's okay, prints a message and exits with success status.
If not, prints a message and exits with failure status.
"""
from django.core.management.base import BaseCommand, CommandError

from basket import BasketException, lookup_user
from basket.errors import BASKET_UNKNOWN_EMAIL

from mozillians.users import tasks


class Command(BaseCommand):
    args = '(no args)'
    help = 'Checks whether Basket is accessible and working'

    def handle(self, *args, **options):

        # Mozillians has some settings that must be set, or it'll just skip talking to Basket.
        # The tasks module looks these up at import time, and might get BASKET_API_KEY
        # from the environment rather than settings if it's there, so look directly at
        # what values the tasks module ended up with.
        required_settings = ['BASKET_API_KEY', 'BASKET_NDA_NEWSLETTER',
                             'BASKET_URL', 'BASKET_VOUCHED_NEWSLETTER']
        if not all([getattr(tasks, setting, False) for setting in required_settings]):
            # At least one is missing. Show what's set and what's missing:
            for setting in required_settings:
                val = getattr(tasks, setting, False)
                if not val:
                    self.stdout.write('** %s is not set and must be **\n' % setting)
                else:
                    self.stdout.write('%s=%s\n' % (setting, val))
            raise CommandError('ERROR: Basket is not enabled with current settings')

        email = 'no_such_person@example.com'

        try:
            lookup_user(email=email)
        except BasketException as exception:
            if exception.code != BASKET_UNKNOWN_EMAIL:
                raise CommandError('ERROR: Error querying basket: %s' % exception)

        # basket.lookup_user will have queried Exact Target for the user's subscriptions,
        # or whether the user exists, and failed if it couldn't get to Exact Target.  Since we got
        # this far, we know things are okay all the way through to Exact Target.
        self.stdout.write('Basket is working okay.\n')
