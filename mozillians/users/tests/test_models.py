# -*- coding: utf-8 -*-
import unittest
from datetime import datetime
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db.models.query import QuerySet
from django.test import override_settings
from django.utils.timezone import make_aware, now

import pytz
from mock import Mock, patch
from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase
from mozillians.groups.models import Group, Skill
from mozillians.groups.tests import (GroupAliasFactory, GroupFactory,
                                     SkillAliasFactory, SkillFactory)
from mozillians.users.managers import (EMPLOYEES, MOZILLIANS, PUBLIC, PUBLIC_INDEXABLE_FIELDS)
from mozillians.users.models import (ExternalAccount, IdpProfile, UserProfile,
                                     _calculate_photo_filename, Vouch)
from mozillians.users.tests import UserFactory


class SignaledFunctionsTests(TestCase):
    def test_auto_create_userprofile(self):
        user = User.objects.create(email='foo@example.com', username='foobar')
        ok_(user.userprofile)

    @patch('mozillians.users.signals.subscribe_user_to_basket.delay')
    @override_settings(BASKET_VOUCHED_NEWSLETTER='foo')
    def test_subscribe_to_basket_post_save(self, subscribe_user_mock):
        user = UserFactory.create()
        subscribe_user_mock.assert_called_with(user.userprofile.id, ['foo'])

    def test_delete_user_obj_on_profile_delete(self):
        user = UserFactory.create()
        profile = user.userprofile
        profile.delete()

        ok_(not User.objects.filter(pk=user.pk).exists())

    @override_settings(CAN_VOUCH_THRESHOLD=1)
    def test_voucher_set_null_on_user_delete(self):
        voucher = UserFactory.create()
        vouchee = UserFactory.create(vouched=False)
        vouchee.userprofile.vouch(voucher.userprofile)
        voucher.delete()
        vouch = Vouch.objects.get(vouchee=vouchee.userprofile)
        eq_(vouch.voucher, None)

    @patch('mozillians.users.signals.subscribe_user_to_basket.delay')
    @override_settings(BASKET_VOUCHED_NEWSLETTER='foo')
    @override_settings(CAN_VOUCH_THRESHOLD=1)
    def test_vouch_is_vouched_gets_updated(self, subscribe_user_mock):
        voucher = UserFactory.create()
        unvouched = UserFactory.create(vouched=False)

        eq_(unvouched.userprofile.is_vouched, False)
        unvouched.userprofile.vouch(voucher.userprofile)

        # Reload from database
        unvouched = User.objects.get(pk=unvouched.id)
        eq_(unvouched.userprofile.is_vouched, True)
        ok_(subscribe_user_mock.called_with(unvouched.userprofile.id, ['foo']))

    @patch('mozillians.users.signals.unsubscribe_from_basket_task.delay')
    @override_settings(BASKET_VOUCHED_NEWSLETTER='foo')
    def test_unvouch_is_vouched_gets_updated(self, unsubscribe_from_basket_mock):
        vouched = UserFactory.create()

        eq_(vouched.userprofile.is_vouched, True)
        vouched.userprofile.vouches_received.all().delete()

        # Reload from database
        vouched = User.objects.get(pk=vouched.id)
        eq_(vouched.userprofile.is_vouched, False)
        ok_(unsubscribe_from_basket_mock.called_with(vouched.userprofile.email, ['foo']))

    @override_settings(CAN_VOUCH_THRESHOLD=5)
    def test_vouch_can_vouch_gets_updated(self):
        unvouched = UserFactory.create(vouched=False)

        # Give four vouches, should not allow to vouch.
        for i in range(4):
            unvouched.userprofile.vouch(None, 'Reason #{0}'.format(i))
            # Reload from database
            unvouched = User.objects.get(pk=unvouched.id)
            eq_(unvouched.userprofile.can_vouch, False)

        # Give the fifth vouch
        unvouched.userprofile.vouch(None)

        # Reload from database
        unvouched = User.objects.get(pk=unvouched.id)
        eq_(unvouched.userprofile.can_vouch, True)

    def test_vouch_alternate_mozilla_address(self):
        user = UserFactory.create(vouched=False)
        user.userprofile.externalaccount_set.create(type=ExternalAccount.TYPE_EMAIL,
                                                    identifier='test@mozilla.com')
        vouch_query = Vouch.objects.filter(vouchee=user.userprofile, autovouch=True,
                                           description=settings.AUTO_VOUCH_REASON)
        eq_(vouch_query.count(), 1)
        eq_(user.userprofile.is_vouched, True)

    def test_vouch_multiple_mozilla_alternate_emails(self):
        user = UserFactory.create(vouched=False)
        user.userprofile.externalaccount_set.create(type=ExternalAccount.TYPE_EMAIL,
                                                    identifier='test1@mozilla.com')
        user.userprofile.externalaccount_set.create(type=ExternalAccount.TYPE_EMAIL,
                                                    identifier='test2@mozilla.com')
        vouch_query = Vouch.objects.filter(vouchee=user.userprofile, autovouch=True,
                                           description=settings.AUTO_VOUCH_REASON)
        eq_(vouch_query.count(), 1)
        eq_(user.userprofile.is_vouched, True)

    def test_vouch_non_mozilla_alternate_email(self):
        user = UserFactory.create(vouched=False)
        user.userprofile.externalaccount_set.create(type=ExternalAccount.TYPE_EMAIL,
                                                    identifier='test@example.com')
        eq_(Vouch.objects.filter(vouchee=user.userprofile).count(), 0)
        eq_(user.userprofile.is_vouched, False)

    def test_vouch_mozilla_email_as_primary(self):
        user = UserFactory.create(vouched=False, email='test1@mozilla.com')
        eq_(Vouch.objects.filter(vouchee=user.userprofile).count(), 1)
        eq_(user.userprofile.is_vouched, True)
        user.userprofile.externalaccount_set.create(type=ExternalAccount.TYPE_EMAIL,
                                                    identifier='test2@example.com')
        eq_(Vouch.objects.filter(vouchee=user.userprofile).count(), 1)

    def change_alternate_mozilla_email_to_primary(self):
        user = UserFactory.create(vouched=False, email='test@example.com')
        alternate_email = user.userprofile.externalaccount_set.create(
            type=ExternalAccount.TYPE_EMAIL, identifier='test@mozilla.com')

        with self.login(user) as client:
            url = reverse('phonebook:change_primary_email', args=[alternate_email.pk])
            client.get(url, follow=True)
        user = User.objects.get(pk=user.pk)
        eq_(user.email, 'test@mozilla.com')
        eq_(user.userprofile.is_vouched, True)
        vouch_query = Vouch.objects.filter(vouchee=user.userprofile, autovouch=True,
                                           description=settings.AUTO_VOUCH_REASON)
        eq_(vouch_query.count(), 1)


class UserProfileTests(TestCase):
    @patch('mozillians.users.models.UserProfile.privacy_fields')
    def test_get_attribute_without_privacy_level(self, mock_privacy_fields):
        mock_privacy_fields.return_value = {'full_name': ''}
        user = UserFactory.create(userprofile={'full_name': 'foobar'})
        eq_(user.userprofile.full_name, 'foobar')

    @patch('mozillians.users.models.UserProfile.privacy_fields')
    def test_get_attribute_with_public_level(self, mock_privacy_fields):
        mock_privacy_fields.return_value = {'full_name': ''}
        user = UserFactory.create(userprofile={'full_name': 'foobar'})
        profile = user.userprofile
        profile.set_instance_privacy_level(PUBLIC)
        eq_(profile.full_name, '')

    @patch('mozillians.users.models.UserProfile.privacy_fields')
    def test_get_attribute_with_employee_level(self, mock_privacy_fields):
        mock_privacy_fields.return_value = {'full_name': ''}
        user = UserFactory.create(userprofile={'full_name': 'foobar'})
        profile = user.userprofile
        profile.set_instance_privacy_level(EMPLOYEES)
        eq_(profile.full_name, 'foobar')

    def test_accounts_access(self):
        user = UserFactory.create()
        user.userprofile.externalaccount_set.create(type=ExternalAccount.TYPE_SUMO,
                                                    identifier='test')
        ok_(isinstance(user.userprofile.accounts, QuerySet))
        eq_(user.userprofile.accounts.filter(identifier='test')[0].identifier, 'test')

    def test_accounts_public_mozillians(self):
        profile = UserFactory.create().userprofile
        profile.set_instance_privacy_level(PUBLIC)
        profile.externalaccount_set.create(type=ExternalAccount.TYPE_SUMO,
                                           identifier='test',
                                           privacy=MOZILLIANS)
        eq_(profile.accounts.count(), 0)
        profile.set_instance_privacy_level(MOZILLIANS)
        eq_(profile.accounts.count(), 1)

    def test_websites(self):
        profile = UserFactory.create().userprofile
        profile.set_instance_privacy_level(MOZILLIANS)
        profile.externalaccount_set.create(type=ExternalAccount.TYPE_SUMO,
                                           identifier='test',
                                           privacy=MOZILLIANS)
        profile.externalaccount_set.create(type=ExternalAccount.TYPE_WEBSITE,
                                           identifier='http://google.com',
                                           privacy=MOZILLIANS)
        eq_(profile.accounts.count(), 1)
        eq_(profile.websites.count(), 1)
        profile.set_instance_privacy_level(PUBLIC)
        eq_(profile.websites.count(), 0)

    def test_annotated_tags_not_public(self):
        # Group member who wants their groups kept semi-private
        profile = UserFactory.create(userprofile={'privacy_groups': MOZILLIANS}).userprofile
        group = GroupFactory.create(name='group')
        group.add_member(profile)

        # Being accessed by a member of the general public
        profile.set_instance_privacy_level(PUBLIC)

        # no groups seen
        eq_(len(profile.get_annotated_tags()), 0)

    def test_annotated_access_groups_not_public(self):
        # Group member who wants their groups kept semi-private
        profile = UserFactory.create(userprofile={'privacy_groups': MOZILLIANS}).userprofile
        group = GroupFactory.create(name='group')
        group.add_member(profile)

        # Being accessed by a member of the general public
        profile.set_instance_privacy_level(PUBLIC)

        # no groups seen
        eq_(len(profile.get_annotated_access_groups()), 0)

    def test_get_annotated_tags_limit_to_current_user(self):
        """Test that get_annotated_tags() limits query to current user.

        To regression test against 969920: We didn't limit
        GroupMembership queryset to current user which resulted server
        timeouts because we iterated over all groups.

        """
        group_1 = GroupFactory.create()
        user_1 = UserFactory.create()
        user_2 = UserFactory.create()
        group_1.add_member(user_1.userprofile)
        group_1.add_member(user_2.userprofile)
        user_groups = user_1.userprofile.get_annotated_tags()
        eq_([group_1], user_groups)

    def test_get_annotated_tags_only_visible(self):
        """ Test that get_annotated_tags() only returns visible groups

        """
        group_1 = GroupFactory.create(visible=True)
        group_2 = GroupFactory.create(visible=False)
        profile = UserFactory.create().userprofile
        group_1.add_member(profile)
        group_2.add_member(profile)

        user_groups = profile.get_annotated_tags()
        eq_([group_1], user_groups)

    def test_get_annotated_access_groups_only_visible(self):
        """ Test that get_annotated_access_groups() only returns visible groups

        """
        group_1 = GroupFactory.create(visible=True, is_access_group=True)
        group_2 = GroupFactory.create(visible=False, is_access_group=True)
        profile = UserFactory.create().userprofile
        group_1.add_member(profile)
        group_2.add_member(profile)

        user_groups = profile.get_annotated_access_groups()
        eq_([group_1], user_groups)

    @patch('mozillians.users.models.UserProfile.auto_vouch')
    def test_auto_vouch_on_profile_save(self, auto_vouch_mock):
        UserFactory.create()
        ok_(auto_vouch_mock.called)

    @patch('mozillians.users.models.send_mail')
    def test_email_now_vouched(self, send_mail_mock):
        user = UserFactory.create()
        user.userprofile._email_now_vouched(None)
        ok_(send_mail_mock.called)
        eq_(send_mail_mock.call_args[0][3], [user.email])

    @override_settings(CAN_VOUCH_THRESHOLD=1)
    @patch('mozillians.users.models.send_mail')
    def test_email_now_vouched_with_voucher(self, send_mail_mock):
        voucher = UserFactory.create()
        user = UserFactory.create(vouched=False)
        user.userprofile._email_now_vouched(voucher.userprofile)
        ok_(send_mail_mock.called)
        eq_(send_mail_mock.call_args[0][3], [user.email])
        ok_(voucher.userprofile.full_name in send_mail_mock.call_args[0][1])

    @patch('mozillians.users.models.send_mail')
    @patch('mozillians.users.models.get_template')
    def test_email_now_vouched_first_vouch(self, get_template_mock, send_mail_mock):
        user = UserFactory.create()
        user.userprofile._email_now_vouched(None)
        eq_(get_template_mock().render.call_args[0][0]['first_vouch'], True)

    @patch('mozillians.users.models.send_mail')
    @patch('mozillians.users.models.get_template')
    @override_settings(CAN_VOUCH_THRESHOLD=2)
    def test_email_now_vouched_can_vouch(self, get_template_mock, send_mail_mock):
        user = UserFactory.create()
        user.userprofile._email_now_vouched(None)
        eq_(get_template_mock().render.call_args_list[0][0][0]['can_vouch_threshold'], False)
        Vouch.objects.create(voucher=None, vouchee=user.userprofile, date=now())
        user.userprofile._email_now_vouched(None)
        eq_(get_template_mock().render.call_args_list[1][0][0]['can_vouch_threshold'], True)

    def test_set_privacy_level_with_save(self):
        user = UserFactory.create()
        user.userprofile.set_privacy_level(9)
        user = User.objects.get(id=user.id)
        for field in UserProfile.privacy_fields():
            eq_(getattr(user.userprofile, 'privacy_{0}'.format(field)), 9,
                'Field {0} not set'.format(field))

    def test_set_privacy_level_without_save(self):
        user = UserFactory.create()
        user.userprofile.set_privacy_level(9, save=False)
        for field in UserProfile.privacy_fields():
            eq_(getattr(user.userprofile, 'privacy_{0}'.format(field)), 9,
                'Field {0} not set'.format(field))
        user = User.objects.get(id=user.id)
        for field in UserProfile.privacy_fields():
            # Compare to default privacy setting for each field.
            f = UserProfile._meta.get_field('privacy_{0}'.format(field))
            eq_(getattr(user.userprofile, 'privacy_{0}'.format(field)),
                f.default, 'Field {0} not set'.format(field))

    def test_set_instance_privacy_level(self):
        user = UserFactory.create()
        user.userprofile.set_instance_privacy_level(9)
        eq_(user.userprofile._privacy_level, 9)

    def test_email_no_privacy(self):
        user = UserFactory.create()
        eq_(user.userprofile.email, user.email)

    def test_email_private(self):
        user = UserFactory.create()
        public_profile = user.userprofile
        public_profile.set_instance_privacy_level(PUBLIC)
        eq_(public_profile.email, UserProfile.privacy_fields()['email'])

    def test_email_public(self):
        user = UserFactory.create(userprofile={'privacy_email': PUBLIC})
        public_profile = user.userprofile
        public_profile.set_instance_privacy_level(PUBLIC)
        eq_(public_profile.email, user.email)

    def test_tshirt_public(self):
        user = UserFactory.create(userprofile={'tshirt': 9})
        public_profile = user.userprofile
        public_profile.set_instance_privacy_level(PUBLIC)
        eq_(public_profile.tshirt, UserProfile.privacy_fields()['tshirt'])

    def test_privacy_level_employee(self):
        user = UserFactory.create()
        group, _ = Group.objects.get_or_create(name='staff')
        group.add_member(user.userprofile)
        eq_(user.userprofile.privacy_level, EMPLOYEES)

    def test_privacy_level_vouched(self):
        user = UserFactory.create()
        eq_(user.userprofile.privacy_level, MOZILLIANS)

    def test_privacy_level_unvouched(self):
        user = UserFactory.create(vouched=False)
        eq_(user.userprofile.privacy_level, PUBLIC)

    def test_is_complete(self):
        user = UserFactory.create(userprofile={'full_name': 'foo bar'})
        ok_(user.userprofile.is_complete)

    def test_is_not_complete(self):
        user = UserFactory.create(userprofile={'full_name': ''})
        ok_(not user.userprofile.is_complete)

    def test_is_public(self):
        for field in UserProfile.privacy_fields():
            user = UserFactory.create(
                userprofile={'privacy_{0}'.format(field): PUBLIC})
            ok_(user.userprofile.is_public,
                'Field {0} did not set profile to public'.format(field))

    def test_is_not_public(self):
        user = UserFactory.create()
        ok_(not user.userprofile.is_public)

    def test_is_public_indexable(self):
        for field in PUBLIC_INDEXABLE_FIELDS:
            user = UserFactory.create(
                userprofile={'privacy_{0}'.format(field): PUBLIC,
                             'ircname': 'bar'})
            ok_(user.userprofile.is_public_indexable,
                'Field {0} did not set profile to public index'.format(field))

    def test_set_membership_group_matches_alias(self):
        group_1 = GroupFactory.create(name='foo')
        group_2 = GroupFactory.create(name='lo')
        GroupAliasFactory.create(alias=group_2, name='bar')
        user = UserFactory.create()
        user.userprofile.set_membership(Group, ['foo', 'bar'])
        eq_(set(user.userprofile.groups.all()), set([group_1, group_2]))

    def test_set_membership_group_new_group(self):
        user = UserFactory.create()
        user.userprofile.set_membership(Group, ['foo', 'bar'])
        ok_(user.userprofile.groups.filter(name='foo').exists())
        ok_(user.userprofile.groups.filter(name='bar').exists())

    def test_set_membership_system_group(self):
        # a "system" group is invisible and cannot be joined or left
        group_1 = GroupFactory.create(visible=False, members_can_leave=False,
                                      accepting_new_members='no')
        user = UserFactory.create()
        user.userprofile.set_membership(Group, [group_1.name, 'bar'])
        ok_(user.userprofile.groups.filter(name='bar').exists())
        eq_(user.userprofile.groups.count(), 1)

    def test_set_membership_skill_matches_alias(self):
        group_1 = SkillFactory.create(name='foo')
        group_2 = SkillFactory.create(name='lo')
        SkillAliasFactory.create(alias=group_2, name='bar')
        user = UserFactory.create()
        user.userprofile.set_membership(Skill, ['foo', 'bar'])
        eq_(set(user.userprofile.skills.all()), set([group_1, group_2]))

    def test_set_membership_skill_new_group(self):
        user = UserFactory.create()
        user.userprofile.set_membership(Skill, ['foo', 'bar'])
        ok_(user.userprofile.skills.filter(name='foo').exists())
        ok_(user.userprofile.skills.filter(name='bar').exists())

    @patch('mozillians.users.models.default_storage')
    @patch('mozillians.users.models.Image')
    @patch('mozillians.users.models.get_thumbnail')
    def test_get_photo_thumbnail_with_photo(self, get_thumbnail_mock, mock_image, mock_storage):
        mock_image_obj = Mock()
        mock_image_obj.mode = 'RGB'
        mock_image.open.return_value = mock_image_obj
        mock_storage.exists.return_value = True
        user = UserFactory.create(userprofile={'photo': 'foo'})
        user.userprofile.get_photo_thumbnail(geometry='geo', crop='crop')
        get_thumbnail_mock.assert_called_with('foo', 'geo', crop='crop')

    @override_settings(DEFAULT_AVATAR_PATH='bar')
    @patch('mozillians.users.models.get_thumbnail')
    def test_get_photo_thumbnail_without_photo(self, get_thumbnail_mock):
        user = UserFactory.create()
        user.userprofile.get_photo_thumbnail(geometry='geo', crop='crop')
        get_thumbnail_mock.assert_called_with('bar', 'geo', crop='crop')

    @patch('mozillians.users.models.UserProfile.get_photo_thumbnail')
    def test_get_photo_url_with_photo(self, get_photo_thumbnail_mock):
        user = UserFactory.create(userprofile={'photo': 'foo'})
        user.userprofile.get_photo_url('80x80', firefox='rocks')
        get_photo_thumbnail_mock.assert_called_with('80x80', firefox='rocks')

    @patch('mozillians.users.models.gravatar')
    def test_get_photo_url_without_photo(self, gravatar_mock):
        user = UserFactory.create()
        user.userprofile.get_photo_url('80x80', firefox='rocks')
        gravatar_mock.assert_called_with(user.email, size='80x80')

    def test_is_not_public_indexable(self):
        user = UserFactory.create()
        ok_(not user.userprofile.is_public_indexable)

    def test_get_absolute_url(self):
        user = UserFactory.create()
        ok_(user.userprofile.get_absolute_url())

    def test_language_privacy_public(self):
        """Test that instance with level PUBLIC cannot access languages."""
        profile = UserFactory.create().userprofile
        profile.language_set.create(code='en')
        profile.privacy_language = MOZILLIANS
        profile.save()
        profile.set_instance_privacy_level(PUBLIC)
        eq_(profile.languages.count(), 0)

    def test_language_privacy_mozillians(self):
        """Test that instance with level MOZILLIANS can access languages."""
        profile = UserFactory.create().userprofile
        profile.language_set.create(code='en')
        profile.privacy_language = MOZILLIANS
        profile.save()
        profile.set_instance_privacy_level(MOZILLIANS)
        eq_(profile.languages.count(), 1)

    def test_is_manager_when_manager(self):
        user = UserFactory.create(manager=True)
        ok_(user.userprofile.is_manager)

    def test_is_manager_when_not_manager(self):
        user = UserFactory.create()
        ok_(not user.userprofile.is_manager)

    def test_is_manager_when_superuser(self):
        user = UserFactory.create(is_superuser=True)
        ok_(user.userprofile.is_manager)

    @override_settings(NDA_GROUP='foobar')
    def test_is_nda_when_member(self):
        user = UserFactory.create()
        group = GroupFactory.create(name='foobar')
        group.add_member(user.userprofile)
        ok_(user.userprofile.is_nda)

    @override_settings(NDA_GROUP='foobar')
    def test_is_nda_when_pending(self):
        user = UserFactory.create()
        group = GroupFactory.create(name='foobar')
        group.add_member(user.userprofile, status='PENDING')
        ok_(not user.userprofile.is_nda)

    @override_settings(NDA_GROUP='foobar')
    def test_is_nda_when_not_member(self):
        user = UserFactory.create()
        GroupFactory.create(name='foobar')
        ok_(not user.userprofile.is_nda)


class VouchTests(TestCase):
    @override_settings(CAN_VOUCH_THRESHOLD=1)
    @override_settings(AUTO_VOUCH_DOMAINS=['example.com'])
    def test_auto_vouching(self):
        UserFactory.create(email='no-reply@mozillians.org')
        user_1 = UserFactory.create(vouched=False, email='foo@example.com')
        user_1 = User.objects.get(pk=user_1.pk)
        ok_(user_1.userprofile.is_vouched)
        eq_(user_1.userprofile.vouches_received.all()[0].autovouch, True)

        user_2 = UserFactory.create(vouched=False, email='foo@bar.com')
        ok_(not user_2.userprofile.is_vouched)

    @override_settings(CAN_VOUCH_THRESHOLD=1)
    @patch('mozillians.users.models.UserProfile._email_now_vouched')
    @patch('mozillians.users.models.now')
    def test_vouch(self, datetime_mock, email_vouched_mock):
        dt = make_aware(datetime(2012, 01, 01, 00, 10), pytz.UTC)
        datetime_mock.return_value = dt
        user_1 = UserFactory.create()
        user_2 = UserFactory.create(vouched=False)
        user_2.userprofile.vouch(user_1.userprofile)
        user_2 = User.objects.get(id=user_2.id)
        ok_(user_2.userprofile.is_vouched)
        eq_(user_2.userprofile.vouched_by, user_1.userprofile)
        eq_(user_2.userprofile.vouches_received.all()[0].date, dt)
        ok_(email_vouched_mock.called)

    @override_settings(CAN_VOUCH_THRESHOLD=1)
    def test_vouch_autovouchset(self):
        # autovouch=False
        user = UserFactory.create(vouched=False)
        user.userprofile.vouch(None, autovouch=False)
        user = User.objects.get(id=user.id)
        ok_(user.userprofile.is_vouched)
        eq_(user.userprofile.vouches_received.all()[0].autovouch, False)

        # autovouch=True
        user = UserFactory.create(vouched=False)
        user.userprofile.vouch(None, autovouch=True)
        user = User.objects.get(id=user.id)
        ok_(user.userprofile.is_vouched)
        eq_(user.userprofile.vouches_received.all()[0].autovouch, True)

    @override_settings(CAN_VOUCH_THRESHOLD=1)
    def test_voucher_public(self):
        voucher = UserFactory.create()
        user = UserFactory.create(vouched=False)
        user.userprofile.vouch(voucher.userprofile)
        voucher_profile = voucher.userprofile
        voucher_profile.privacy_full_name = PUBLIC
        voucher_profile.save()
        user_profile = user.userprofile
        user_profile.set_instance_privacy_level(PUBLIC)

        eq_(user_profile.vouched_by, voucher.userprofile)

    def test_voucher_nonpublic(self):
        voucher = UserFactory.create()
        user = UserFactory.create()
        user.userprofile.vouch(voucher.userprofile)
        user_profile = user.userprofile
        user_profile.set_instance_privacy_level(PUBLIC)

        eq_(user_profile.vouched_by, None)

    def test_vouchee_privacy(self):
        voucher = UserFactory.create()
        vouchee_1 = UserFactory.create(userprofile={'privacy_full_name': PUBLIC})
        vouchee_2 = UserFactory.create(userprofile={'privacy_full_name': MOZILLIANS})

        vouchee_1.userprofile.vouch(voucher.userprofile)
        vouchee_2.userprofile.vouch(voucher.userprofile)
        user_profile = voucher.userprofile
        user_profile.set_instance_privacy_level(PUBLIC)
        eq_(set(user_profile.vouches_made.all()),
            set(vouchee_1.userprofile.vouches_received.filter(voucher=user_profile)))

        user_profile.set_instance_privacy_level(MOZILLIANS)
        eq_(set(user_profile.vouches_made.all()), set(Vouch.objects.filter(voucher=user_profile)))

    def test_vouch_reset(self):
        voucher = UserFactory.create()
        user = UserFactory.create()
        user.userprofile.vouch(voucher.userprofile)
        profile = user.userprofile
        profile.vouches_received.all().delete()
        profile.is_vouched = False
        profile.save()
        profile = UserProfile.objects.get(pk=profile.id)
        ok_(not profile.vouches_received.all())

    @override_settings(CAN_VOUCH_THRESHOLD=1)
    def test_vouch_once_per_voucher(self):
        voucher = UserFactory.create()
        user = UserFactory.create(vouched=False)
        user.userprofile.vouch(voucher.userprofile)
        user.userprofile.vouch(voucher.userprofile)
        eq_(user.userprofile.vouches_received.all().count(), 1)

    @override_settings(CAN_VOUCH_THRESHOLD=1)
    @override_settings(VOUCH_COUNT_LIMIT=2)
    def test_multiple_vouches(self):
        user = UserFactory.create(vouched=False)
        # 9 vouches, only 2 should stick.
        for i in range(1, 10):
            user.userprofile.vouch(UserFactory.create().userprofile)
        eq_(user.userprofile.vouches_received.all().count(), 2)


class CalculatePhotoFilenameTests(TestCase):
    @patch('mozillians.users.models.uuid.uuid4', wraps=uuid4)
    def test_base(self, uuid4_mock):
        result = _calculate_photo_filename(None, '')
        ok_(result.endswith('.jpg'))
        ok_(result.startswith(settings.USER_AVATAR_DIR))
        ok_(uuid4_mock.called)


class ExternalAccountTests(TestCase):
    def test_get_url(self):
        profile = UserFactory.create().userprofile
        account = profile.externalaccount_set.create(type=ExternalAccount.TYPE_MDN,
                                                     identifier='sammy')
        ok_('sammy' in account.get_identifier_url())

    def test_get_url_unicode(self):
        profile = UserFactory.create().userprofile
        account = profile.externalaccount_set.create(type=ExternalAccount.TYPE_MDN,
                                                     identifier=u'sammyウ')
        ok_('%E3%82%A6' in account.get_identifier_url())

    def test_urls_contain_identifiers(self):
        for value, account in ExternalAccount.ACCOUNT_TYPES.iteritems():
            if account['url']:
                ok_('{identifier}' in account['url'])


class EmailAttributeTests(TestCase):
    def test_existing_idp_privacy_unaware(self):
        profile = UserFactory.create(email='foo@foo.com').userprofile
        IdpProfile.objects.create(
            profile=profile,
            auth0_user_id='github|foo@bar.com',
            email='foo@bar.com',
            primary=True,
            primary_contact_identity=True,
            privacy=PUBLIC
        )

        eq_(profile.email, 'foo@bar.com')

    def test_existing_idp_privacy_allowed(self):
        profile = UserFactory.create(email='foo@foo.com').userprofile
        profile.set_instance_privacy_level(MOZILLIANS)
        IdpProfile.objects.create(
            profile=profile,
            auth0_user_id='github|foo@bar.com',
            email='foo@bar.com',
            primary=True,
            primary_contact_identity=True,
            privacy=PUBLIC
        )

        eq_(profile.email, 'foo@bar.com')

    def test_existing_idp_privacy_not_allowed(self):
        profile = UserFactory.create(email='foo@foo.com').userprofile
        profile.set_instance_privacy_level(PUBLIC)
        IdpProfile.objects.create(
            profile=profile,
            auth0_user_id='github|foo@bar.com',
            email='foo@bar.com',
            primary=True,
            primary_contact_identity=True,
            privacy=MOZILLIANS
        )

        eq_(profile.email, '')

    def test_not_existing_idp_privacy_unaware(self):
        profile = UserFactory.create(email='foo@foo.com').userprofile
        eq_(profile.email, 'foo@foo.com')

    def test_not_existing_idp_privacy_allowed(self):
        userprofile_args = {
            'privacy_email': PUBLIC
        }
        profile = UserFactory.create(email='foo@foo.com', userprofile=userprofile_args).userprofile
        profile.set_instance_privacy_level(MOZILLIANS)
        eq_(profile.email, 'foo@foo.com')

    def test_not_existing_idp_privacy_not_allowed(self):
        userprofile_args = {
            'privacy_email': MOZILLIANS
        }
        profile = UserFactory.create(email='foo@foo.com', userprofile=userprofile_args).userprofile
        profile.set_instance_privacy_level(PUBLIC)
        eq_(profile.email, '')


class PrivacyModelTests(unittest.TestCase):
    def setUp(self):
        UserProfile.clear_privacy_fields_cache()

    def test_profile_model(self):
        fields = UserProfile.privacy_fields()
        eq_('', fields['ircname'])
        eq_('', fields['email'])
        ok_('is_vouched' not in fields)
        ok_('date_vouched' not in fields)
        ok_(fields['tshirt'] is None)

    def test_caching(self):
        # It would be better if this test didn't need to know how the
        # caching worked.
        # To compute the privacy fields, the code has to get all the
        # field names. Use mock so we can tell if that gets called.
        with patch.object(UserProfile._meta, 'get_field') as mock_get_field:
            UserProfile.privacy_fields()
        ok_(mock_get_field.called)
        # If we call privacy_fields() again, it shouldn't need to compute it all again
        with patch.object(UserProfile._meta, 'get_field') as mock_get_field:
            UserProfile.privacy_fields()
        ok_(not mock_get_field.called)


class CISHelperMethodsTests(unittest.TestCase):
    def tearDown(self):
        Group.objects.all().delete()
        IdpProfile.objects.all().delete()

    def test_cis_emails_without_primary_identity(self):
        profile = UserFactory.create(email='foo@bar.com').userprofile

        expected_result = [
            {
                'value': 'foo@bar.com',
                'verified': True,
                'primary': True,
                'name': 'mozillians-primary-{0}'.format(profile.id)
            },
        ]
        eq_(profile.get_cis_emails(), expected_result)

    def test_cis_emails_with_primary_identity(self):
        profile = UserFactory.create(email='foo@bar.com').userprofile
        IdpProfile.objects.create(
            profile=profile,
            auth0_user_id='github|1',
            email='foo@bar.com',
            primary=True,
        )

        expected_result = [
            {
                'value': u'foo@bar.com',
                'verified': True,
                'primary': True,
                'name': u'Github Provider'
            }
        ]
        eq_(profile.get_cis_emails(), expected_result)

    def test_cis_groups_highest(self):
        user = UserFactory.create()
        group1 = GroupFactory.create(name='nda',
                                     is_access_group=True)
        group2 = GroupFactory.create(name='cis_whitelist',
                                     is_access_group=True)
        group3 = GroupFactory.create(name='open innovation + reps council',
                                     is_access_group=True)
        group4 = GroupFactory.create(name='group4')
        group1.add_member(user.userprofile)
        group2.add_member(user.userprofile)
        group3.add_member(user.userprofile)
        group4.add_member(user.userprofile, status='PENDING')
        IdpProfile.objects.create(
            profile=user.userprofile,
            auth0_user_id='github|foo@bar.com',
            primary=False,
        )
        idp = IdpProfile.objects.create(
            profile=user.userprofile,
            auth0_user_id='ad|foo@bar.com',
            primary=True,
        )

        eq_(set(user.userprofile.get_cis_groups(idp)),
            set(['mozilliansorg_nda', 'mozilliansorg_cis_whitelist',
                 'mozilliansorg_open-innovation-reps-council']))

    def test_cis_groups_not_highest(self):
        user = UserFactory.create()
        group1 = GroupFactory.create(name='nda')
        group2 = GroupFactory.create(name='cis_whitelist')
        group3 = GroupFactory.create(name='group3')
        group1.add_member(user.userprofile)
        group2.add_member(user.userprofile)
        group3.add_member(user.userprofile, status='PENDING')
        idp = IdpProfile.objects.create(
            profile=user.userprofile,
            auth0_user_id='github|foo@bar.com',
            primary=False,
        )
        IdpProfile.objects.create(
            profile=user.userprofile,
            auth0_user_id='ad|foo@bar.com',
            primary=True,
        )

        eq_(user.userprofile.get_cis_groups(idp), [])

    def test_cis_groups_not_mfa(self):
        user = UserFactory.create()
        group1 = GroupFactory.create(name='nda')
        group2 = GroupFactory.create(name='cis_whitelist')
        group3 = GroupFactory.create(name='group3')
        group1.add_member(user.userprofile)
        group2.add_member(user.userprofile)
        group3.add_member(user.userprofile, status='PENDING')
        idp = IdpProfile.objects.create(
            profile=user.userprofile,
            auth0_user_id='email|foo@bar.com',
            email='foo@bar.com',
            primary=False,
        )
        IdpProfile.objects.create(
            profile=user.userprofile,
            auth0_user_id='email|bar@bar.com',
            email='bar@bar.com',
            primary=True,
        )

        eq_(user.userprofile.get_cis_groups(idp), [])

    def test_cis_groups_without_idp_profile(self):
        user = UserFactory.create()
        user1 = UserFactory.create()
        group1 = GroupFactory.create(name='nda')
        group2 = GroupFactory.create(name='cis_whitelist')
        group3 = GroupFactory.create(name='group3')
        group1.add_member(user.userprofile)
        group2.add_member(user.userprofile)
        group3.add_member(user.userprofile, status='PENDING')
        idp = IdpProfile.objects.create(
            profile=user1.userprofile,
            auth0_user_id='github|foo@bar.com',
            primary=False,
        )

        eq_(user.userprofile.get_cis_groups(idp), [])

    def test_cis_tags(self):
        user = UserFactory.create()
        group1 = GroupFactory.create(name='foo',
                                     is_access_group=False)
        group2 = GroupFactory.create(name='bar',
                                     is_access_group=False)
        group3 = GroupFactory.create(name='baz',
                                     is_access_group=False)
        group1.add_member(user.userprofile)
        group2.add_member(user.userprofile)
        group3.add_member(user.userprofile, status='PENDING')
        IdpProfile.objects.create(
            profile=user.userprofile,
            auth0_user_id='ad|foo@bar.com',
            primary=True,
        )

        eq_(set(user.userprofile.get_cis_tags()),
            set(['foo', 'bar']))

    def test_cis_uris(self):
        user = UserFactory.create()
        sumo_uri = user.userprofile.externalaccount_set.create(
            type=ExternalAccount.TYPE_SUMO,
            identifier='test'
        )

        expected_result = [
            {
                'value': 'https://support.mozilla.org/user/test',
                'primary': False,
                'verified': False,
                'name': 'mozillians-Mozilla Support-{}'.format(sumo_uri.pk)
            }
        ]

        eq_(user.userprofile.get_cis_uris(), expected_result)
