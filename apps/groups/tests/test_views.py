from funfactory.urlresolvers import reverse
from nose.tools import eq_

import apps.common.tests.init
from apps.groups.models import Group
from apps.users.models import PUBLIC

class ViewsTest(apps.common.tests.init.ESTestCase):
    def setUp(self):
        super(ViewsTest, self).setUp()
        lala_group, _ = Group.objects.get_or_create(name='lala', system=True)
        for user in [self.mozillian, self.mozillian2, self.pending]:
            lala_group.members.add(user.userprofile)

    def test_public_groups_with_indexable_user_no_group_perm(self):
        url = reverse('group', kwargs={'url': 'lala'})
        response = self.anonymous_client.get(url, follow=True)
        paginator = response.context['people'].paginator
        eq_(paginator.count, 0)

    def test_public_groups_with_indexable_user_with_group_perm(self):
        userprofile = self.mozillian2.userprofile
        userprofile.privacy_groups = PUBLIC
        userprofile.save()
        url = reverse('group', kwargs={'url': 'lala'})
        response = self.anonymous_client.get(url, follow=True)
        paginator = response.context['people'].paginator
        eq_(paginator.count, 1)
        self.assertIn(self.mozillian2.userprofile, paginator.object_list)
        profile = paginator.object_list[0]
        eq_(profile._privacy_level, PUBLIC)
