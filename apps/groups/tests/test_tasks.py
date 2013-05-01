from nose.tools import eq_

from apps.common.tests.init import ESTestCase

from apps.groups.models import Group, Skill
from apps.groups.tasks import remove_empty_groups

class EmptyGroupsTest(ESTestCase):
    """Test Empty Group Removal."""

    def test_empty_group_removal(self):
        """Test Empty Group Removal."""
        for model in [Group, Skill]:
            model.objects.all().delete()
            model.objects.create(name='foo')
            eq_(model.objects.count(), 1)
            remove_empty_groups()
            eq_(model.objects.count(), 0)
