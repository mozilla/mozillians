from funfactory.urlresolvers import reverse

from common.tests import TestCase
from groups.models import Group
from taskboard.models import Task


class TaskTest(TestCase):
    def test_groups_added_to_new_task(self):
        """Test that new groups are created and added to the task"""
        self.mozillian_client.post(
            reverse('taskboard_task_new'),
            data={
                'summary': 'Testing',
                'contact': self.mozillian.pk,
                'groups': 'stuff,whatnot',
                }
        )
        t = Task.objects.get(summary='Testing')
        t_groups = set(g.name for g in t.groups.all())
        self.assertSetEqual(set(['stuff', 'whatnot']), t_groups)

    def test_saving_groups_no_delete_system_groups(self):
        """Test that system groups are not removed when not in the form."""
        # another test may create the 'staff' group and not clean up.
        sys_group, created = Group.objects.get_or_create(name='staff')
        if not sys_group.system:
            sys_group.system = True
            sys_group.save()
        t = Task.objects.create(
            summary='Testing',
            contact=self.mozillian,
        )
        t.groups.add(sys_group)
        # make sure the system group is in there before submitting the post
        self.assertTrue(sys_group in t.groups.all())
        self.mozillian_client.post(
            reverse('taskboard_task_edit', kwargs={'pk': t.pk}),
            data={
                'summary': 'Testing',
                'contact': self.mozillian.pk,
                'groups': 'stuff,whatnot',
            }
        )
        t2 = Task.objects.get(pk=t.pk)
        t2_groups = set(g.name for g in t2.groups.all())
        self.assertSetEqual(set(['stuff', 'whatnot', 'staff']), t2_groups)
