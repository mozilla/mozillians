from nose.tools import eq_

from mozillians.common.tests import TestCase
from mozillians.groups.models import GroupAlias, Group
from mozillians.groups.tests import GroupFactory
from mozillians.users.tests import UserFactory


class TestGroupAdmin(TestCase):
    def test_member_counts(self):
        # The Group admin computes how many vouched members there are
        # and how many overall
        admin_user = UserFactory.create(is_staff=True, is_superuser=True,
                                        userprofile={'is_vouched': True})

        # IMPORTANT: This test is expected to fail on Postgres, and
        # probably other databases where the Boolean type is not just
        # an alias for a small integer. Mozillians is currently
        # deployed on a database where this works. If we ever try
        # deploying it on another database where it doesn't work, this
        # test will alert us quickly that we'll need to take another
        # approach to this feature.

        # Create group with 3 vouched members and 2 unvouched members
        group = GroupFactory(name='web development')
        profiles = []
        for i in range(2):
            profile = UserFactory(userprofile={'is_vouched': False}).userprofile
            group.add_member(profile)
            profiles.append(profile)
        for i in range(3):
            profile = UserFactory(userprofile={'is_vouched': True}).userprofile
            group.add_member(profile)
            profiles.append(profile)

        # Create an alias for our group that will also match our query.
        # This can lead to members being counted multiple times.
        # Another trigger would be searching for a string that appears in the
        # group name more than once.
        GroupAlias.objects.create(alias=group, name='web development alias')

        with self.login(admin_user) as client:
            response = client.get('/admin/groups/group/?q=web+dev')
        eq_(response.status_code, 200)
        change_list = response.context['cl']
        group = change_list.result_list.get(name=group.name)
        eq_(group.member_count, group.members.count())
        eq_(5, group.member_count)
        eq_(group.vouched_member_count, group.members.filter(is_vouched=True).count())
        eq_(3, group.vouched_member_count)

    def test_group_ordering(self):
        # Since we're mucking with the group changelist queryset in a way
        # that could break ordering, make sure it's still working.
        admin_user = UserFactory.create(is_staff=True, is_superuser=True,
                                        userprofile={'is_vouched': True})
        group1 = GroupFactory(name='web development 1')
        group2 = GroupFactory(name='web development 2')
        group3 = GroupFactory(name='web development 3')
        # Create some profiles we can use
        profiles = [UserFactory(userprofile={'is_vouched': True}).userprofile
                    for i in range(3)]
        # Add different numbers of profiles to each group
        for p in profiles[:3]:
            group1.add_member(p)
        for p in profiles[:2]:
            group2.add_member(p)
        for p in profiles[:1]:
            group3.add_member(p)

        # Don't let the staff group confuse the issue
        Group.objects.filter(name='staff').delete()

        col_number = 7  # where the member_count column is
        # It would be better to get the column number using
        # GroupAdmin.list_display.index('member_count') + 1,
        # but importing GroupAdmin from the test breaks the
        # admin autodiscovery somehow, and the group admin URLs
        # don't get registered.

        # Sort by member count
        url = '/admin/groups/group/?o=%d.1' % col_number
        print url
        with self.login(admin_user) as client:
            response = client.get(url)
        eq_(response.status_code, 200)
        change_list = response.context['cl']
        qset = change_list.result_list
        # The group with the fewest members should be first
        eq_([group3, group2, group1], list(qset))

        # Again, in reverse, to make sure the first success wasn't just luck
        url = '/admin/groups/group/?o=-%d.1' % col_number
        print url
        with self.login(admin_user) as client:
            response = client.get(url)
        eq_(response.status_code, 200)
        change_list = response.context['cl']
        qset = change_list.result_list
        # The group with the most members should be first
        eq_([group1, group2, group3], list(qset))
