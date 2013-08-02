# -*- coding: utf-8 -*-
import json

from django.contrib.auth.models import User

from funfactory.urlresolvers import reverse
from nose.tools import eq_

import apps.common.tests.init

from ..cron import assign_autocomplete_to_groups
from ..models import AUTO_COMPLETE_COUNT, Skill


class SkillsTest(apps.common.tests.init.ESTestCase):

    def test_autocomplete_api(self):
        r = self.mozillian_client.get(reverse('skill_search'),
                                      dict(term='daft'),
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
        r = self.mozillian_client.get(reverse('skill_search'),
                                      dict(term='true'),
                                      HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        assert 'true love' in json.loads(r.content)

    def test_pending_user_can_add_skills(self):
        """Ensure pending users can add/edit skills."""
        profile = self.pending.get_profile()
        assert not profile.skills.all(), 'User should have no skills.'

        data = self.data_privacy_fields.copy()
        data.update(dict(full_name='McAwesomepants', country='pl',
                         username='McAwesomepants', skills='Awesome foo Bar'))
        self.pending_client.post(reverse('profile.edit'), data, follow=True)

        assert profile.skills.all(), (
                "Pending user should be able to edit skills.")

    def test_unicode_skills(self):
        """Users can add skills like c++ and φωτογραφία."""
        profile = self.pending.get_profile()
        assert not profile.skills.all(), 'User should have no skills.'

        data = self.data_privacy_fields.copy()
        data.update(dict(full_name='McAwesomepants', country='pl',
                         username='McAwesomepants', skills='c++ φωτογραφί'))
        self.pending_client.post(reverse('profile.edit'), data, follow=True)
		
        assert "c++" in profile.skills.all()[0].name
        assert u"φωτογραφί" in profile.skills.all()[0].name
