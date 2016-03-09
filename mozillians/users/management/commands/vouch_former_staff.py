from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone

from mozillians.common.templatetags.helpers import get_object_or_none
from mozillians.users.models import UserProfile, Vouch


class Command(BaseCommand):

    option_list = list(BaseCommand.option_list) + [
        make_option('--file',
                    dest='file',
                    default=None,
                    help='Path to file with line separated former staff emails.'),
        make_option('--dry-run',
                    dest='dry-run',
                    action='store_true',
                    default=False,
                    help='Run without changing the DB.')
    ]

    def handle(self, *args, **options):
        path = options.get('file', None)
        dry_run = options.get('dry-run')

        if not path:
            raise CommandError('Option --file must be specified')

        try:
            f = open(path)
        except IOError:
            raise CommandError('Invalid file path.')

        now = timezone.now()
        former_employee_descr = 'An automatic vouch for being a former Mozilla employee.'
        employee_descr = 'An automatic vouch for being a Mozilla employee.'

        count = 0
        for email in f:
            u = get_object_or_none(UserProfile, user__email=email.strip())
            if u:
                vouches = u.vouches_received.all()
                already_vouched = vouches.filter(
                    Q(description=employee_descr) |
                    Q(description=former_employee_descr),
                    autovouch=True
                )
                if not already_vouched.exists():
                    if not dry_run:
                        Vouch.objects.create(
                            voucher=None,
                            vouchee=u,
                            autovouch=True,
                            date=now,
                            description=former_employee_descr
                        )
                    count = count + 1

        print "%d former staff members vouched." % count
