import json

from django.contrib.auth.models import User

from funfactory.urlresolvers import reverse
from nose.tools import eq_

import common.tests
from groups.cron import assign_autocomplete_to_groups
from groups.models import AUTO_COMPLETE_COUNT, Skill


class SkillsTest(common.tests.TestCase):
    def test_autocomplete_api(self):
        self.client.login(email=self.mozillian.email)

        r = self.client.get(reverse('skill_search'), dict(term='daft'),
                HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        eq_(r['Content-Type'], 'application/json', 'api uses json header')
        assert not 'daft_punk' in json.loads(r.content)

        # Make enough users in a group to trigger the autocomplete
        robots = Skill.objects.create(name='true love')
        for i in range(0, AUTO_COMPLETE_COUNT + 1):
            email = 'always_angry%s@example.com' % (str(i))
            user = User.objects.create_user(email.split('@')[0], email)
            user.is_active = True
            user.save()
            profile = user.get_profile()
            profile.skills.add(robots)

        assign_autocomplete_to_groups()
        r = self.client.get(reverse('skill_search'), dict(term='true'),
                HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        assert 'true love' in json.loads(r.content)

    def test_pending_user_can_add_skills(self):
        """Ensure pending users can add/edit skills."""
        profile = self.pending.get_profile()
        assert not profile.skills.all(), 'User should have no skills.'

        self.client.login(email=self.pending.email)
        d = dict(self.privacy_dict, last_name='McAwesomepants',
                 skills='Awesome foo Bar')
        self.client.post(reverse('profile.edit'), d, follow=True)

        assert profile.skills.all(), (
                "Pending user should be able to edit skills.")
