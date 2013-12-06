# -*- coding: utf-8 -*-

from datetime import datetime
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.query import QuerySet
from django.test.utils import override_settings
from django.utils import unittest

import basket
from mock import Mock, call, patch
from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase
from mozillians.groups.models import Group, Language, Skill
from mozillians.groups.tests import (GroupAliasFactory, GroupFactory,
                                     LanguageAliasFactory, LanguageFactory,
                                     SkillAliasFactory, SkillFactory)
from mozillians.users.managers import EMPLOYEES, MOZILLIANS, PUBLIC, PUBLIC_INDEXABLE_FIELDS
from mozillians.users.models import ExternalAccount, UserProfile, _calculate_photo_filename
from mozillians.users.tests import UserFactory


class SignaledFunctionsTests(TestCase):
    def test_auto_create_userprofile(self):
        user = User.objects.create(email='foo@example.com', username='foobar')
        ok_(user.userprofile)

    @patch('mozillians.users.models.update_basket_task.delay')
    def test_update_basket_post_save(self, update_basket_mock):
        user = UserFactory.create()
        update_basket_mock.assert_called_with(user.userprofile.id)

    @patch('mozillians.users.models.index_objects.delay')
    @patch('mozillians.users.models.unindex_objects.delay')
    def test_update_index_post_save(self, unindex_objects_mock,
                                    index_objects_mock):
        user = UserFactory.create()
        index_objects_mock.assert_called_with(
            UserProfile, [user.userprofile.id], public_index=False)
        unindex_objects_mock.assert_called_with(
            UserProfile, [user.userprofile.id], public_index=True)

    @patch('mozillians.users.models.index_objects.delay')
    @patch('mozillians.users.models.unindex_objects.delay')
    def test_update_index_post_save_incomplete_profile(self,
                                                       unindex_objects_mock,
                                                       index_objects_mock):
        UserFactory.create(userprofile={'full_name': ''})
        ok_(not index_objects_mock.called)
        ok_(not unindex_objects_mock.called)

    def test_remove_from_index_post_delete(self):
        user = UserFactory.create()

        with patch('mozillians.users.models.unindex_objects.delay') as (
                unindex_objects_mock):
            user.delete()

        unindex_objects_mock.assert_has_calls([
            call(UserProfile, [user.userprofile.id], public_index=False),
            call(UserProfile, [user.userprofile.id], public_index=True)])


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

    def test_extract_document(self):
        group_1 = GroupFactory.create()
        group_2 = GroupFactory.create()
        skill_1 = SkillFactory.create()
        skill_2 = SkillFactory.create()
        language_1 = LanguageFactory.create()
        language_2 = LanguageFactory.create()
        user = UserFactory.create(userprofile={'city': 'athens',
                                               'region': 'attika',
                                               'allows_community_sites': False,
                                               'allows_mozilla_sites': False,
                                               'country': 'gr',
                                               'full_name': 'Nikos Koukos',
                                               'bio': 'This is my bio'})
        profile = user.userprofile
        group_1.add_member(profile)
        group_2.add_member(profile)
        profile.skills.add(skill_1)
        profile.skills.add(skill_2)
        profile.languages.add(language_1)
        profile.languages.add(language_2)

        result = UserProfile.extract_document(user.userprofile.id)
        ok_(isinstance(result, dict))
        eq_(result['id'], profile.id)
        eq_(result['is_vouched'], profile.is_vouched)
        eq_(result['region'], profile.region)
        eq_(result['city'], profile.city)
        eq_(result['allows_community_sites'], profile.allows_community_sites)
        eq_(result['allows_mozilla_sites'], profile.allows_mozilla_sites)
        eq_(result['country'], ['gr', 'greece'])
        eq_(result['fullname'], profile.full_name.lower())
        eq_(result['name'], profile.full_name.lower())
        eq_(result['bio'], profile.bio)
        eq_(result['has_photo'], False)
        eq_(result['groups'], [group_1.name, group_2.name])
        eq_(result['skills'], [skill_1.name, skill_2.name])
        eq_(result['languages'], [language_1.name, language_2.name])

    def test_get_mapping(self):
        ok_(UserProfile.get_mapping())

    @override_settings(ES_INDEXES={'default': 'index'})
    @patch('mozillians.users.models.PrivacyAwareS')
    def test_search_no_public_only_vouched(self, PrivacyAwareSMock):
        result = UserProfile.search('foo')
        ok_(isinstance(result, Mock))
        PrivacyAwareSMock.assert_any_call(UserProfile)
        PrivacyAwareSMock().indexes.assert_any_call('index')
        (PrivacyAwareSMock().indexes().boost()
         .query().order_by().filter.assert_any_call(is_vouched=True))
        ok_(call().privacy_level(PUBLIC) not in PrivacyAwareSMock.mock_calls)

    @override_settings(ES_INDEXES={'default': 'index'})
    @patch('mozillians.users.models.PrivacyAwareS')
    def test_search_no_public_with_unvouched(self, PrivacyAwareSMock):
        result = UserProfile.search('foo', include_non_vouched=True)
        ok_(isinstance(result, Mock))
        PrivacyAwareSMock.assert_any_call(UserProfile)
        PrivacyAwareSMock().indexes.assert_any_call('index')
        ok_(call().indexes().boost()
            .query().order_by().filter(is_vouched=True)
            not in PrivacyAwareSMock.mock_calls)
        ok_(call().privacy_level(PUBLIC) not in PrivacyAwareSMock.mock_calls)

    @override_settings(ES_INDEXES={'public': 'public_index'})
    @patch('mozillians.users.models.PrivacyAwareS')
    def test_search_public_only_vouched(self, PrivacyAwareSMock):
        result = UserProfile.search('foo', public=True)
        ok_(isinstance(result, Mock))
        PrivacyAwareSMock.assert_any_call(UserProfile)
        PrivacyAwareSMock().privacy_level.assert_any_call(PUBLIC)
        (PrivacyAwareSMock().privacy_level()
         .indexes.assert_any_call('public_index'))
        (PrivacyAwareSMock().privacy_level().indexes().boost()
         .query().order_by().filter.assert_any_call(is_vouched=True))

    @override_settings(ES_INDEXES={'public': 'public_index'})
    @patch('mozillians.users.models.PrivacyAwareS')
    def test_search_public_with_unvouched(self, PrivacyAwareSMock):
        result = UserProfile.search(
            'foo', public=True, include_non_vouched=True)
        ok_(isinstance(result, Mock))
        PrivacyAwareSMock.assert_any_call(UserProfile)
        PrivacyAwareSMock().privacy_level.assert_any_call(PUBLIC)
        (PrivacyAwareSMock().privacy_level()
         .indexes.assert_any_call('public_index'))
        ok_(call().privacy_level().indexes().boost()
            .query().order_by().filter(is_vouched=True)
            not in PrivacyAwareSMock.mock_calls)

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

    @patch('mozillians.users.models.UserProfile.auto_vouch')
    def test_auto_vouch_on_profile_save(self, auto_vouch_mock):
        UserFactory.create()
        ok_(auto_vouch_mock.called)

    @patch('mozillians.users.models.UserProfile.add_to_staff_group')
    def test_add_to_staff_group_on_profile_save(self, add_to_staff_group_mock):
        UserFactory.create()
        ok_(add_to_staff_group_mock.called)

    @override_settings(AUTO_VOUCH_DOMAINS=['example.com'])
    def test_add_to_staff_group_auto_vouch_domain(self):
        user = UserFactory.create(email='foobar@example.com')
        ok_(user.userprofile.groups.filter(name='staff').exists())

    @override_settings(AUTO_VOUCH_DOMAINS=['example.com'])
    def test_add_to_staff_group_invalid_domain(self):
        user = UserFactory.create(email='foobar@not_valid.com')
        staff_group, _ = Group.objects.get_or_create(name='staff')
        staff_group.add_member(user.userprofile)
        user.userprofile.add_to_staff_group()
        ok_(not user.userprofile.groups.filter(name='staff').exists())

    @patch('mozillians.users.models.send_mail')
    def test_email_now_vouched(self, send_mail_mock):
        user = UserFactory.create()
        user.userprofile._email_now_vouched()
        ok_(send_mail_mock.called)
        eq_(send_mail_mock.call_args[0][3], [user.email])

    @override_settings(ES_INDEXES={'public': 'foo'})
    def test_get_index_public(self):
        ok_(UserProfile.get_index(public_index=True), 'foo')

    @override_settings(ES_INDEXES={'default': 'bar'})
    def test_get_index(self):
        ok_(UserProfile.get_index(public_index=False), 'bar')

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
            f = UserProfile._meta.get_field_by_name('privacy_{0}'.format(field))[0]
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
        user = UserFactory.create(userprofile={'is_vouched': True})
        eq_(user.userprofile.privacy_level, MOZILLIANS)

    def test_privacy_level_unvouched(self):
        user = UserFactory.create()
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

    def test_set_membership_language_matches_alias(self):
        group_1 = LanguageFactory.create(name='foo')
        group_2 = LanguageFactory.create(name='lo')
        LanguageAliasFactory.create(alias=group_2, name='bar')
        user = UserFactory.create()
        user.userprofile.set_membership(Language, ['foo', 'bar'])
        eq_(set(user.userprofile.languages.all()), set([group_1, group_2]))

    def test_set_membership_language_new_group(self):
        user = UserFactory.create()
        user.userprofile.set_membership(Language, ['foo', 'bar'])
        ok_(user.userprofile.languages.filter(name='foo').exists())
        ok_(user.userprofile.languages.filter(name='bar').exists())

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

    @patch('mozillians.users.models.get_thumbnail')
    def test_get_photo_thumbnail_with_photo(self, get_thumbnail_mock):
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

    @override_settings(AUTO_VOUCH_DOMAINS=['example.com'])
    def test_auto_vouching(self):
        user_1 = UserFactory.create(email='foo@example.com')
        user_2 = UserFactory.create(email='foo@bar.com')
        ok_(user_1.userprofile.is_vouched)
        ok_(not user_2.userprofile.is_vouched)

    @patch('mozillians.users.models.UserProfile._email_now_vouched')
    @patch('mozillians.users.models.datetime')
    def test_vouch(self, datetime_mock, email_vouched_mock):
        datetime_mock.now.return_value = datetime(2012, 01, 01, 00, 10)
        user_1 = UserFactory.create(userprofile={'is_vouched': True})
        user_2 = UserFactory.create()
        user_2.userprofile.vouch(user_1.userprofile)
        user_2 = User.objects.get(id=user_2.id)
        ok_(user_2.userprofile.is_vouched)
        eq_(user_2.userprofile.vouched_by, user_1.userprofile)
        eq_(user_2.userprofile.date_vouched, datetime(2012, 01, 01, 00, 10))
        ok_(email_vouched_mock.called)

    @patch('mozillians.users.models.UserProfile._email_now_vouched')
    def test_vouch_no_commit(self, email_vouched_mock):
        user_1 = UserFactory.create(userprofile={'is_vouched': True})
        user_2 = UserFactory.create()
        user_2.userprofile.vouch(user_1.userprofile, commit=False)
        user_2 = User.objects.get(id=user_2.id)
        ok_(not user_2.userprofile.is_vouched)
        ok_(not user_2.userprofile.vouched_by)
        ok_(not user_2.userprofile.date_vouched)
        ok_(email_vouched_mock.called)

    def test_voucher_public(self):
        voucher = UserFactory.create(userprofile={'is_vouched': True})
        user = UserFactory.create(
            userprofile={'is_vouched': True,
                         'vouched_by': voucher.userprofile})
        voucher_profile = voucher.userprofile
        voucher_profile.privacy_full_name = PUBLIC
        voucher_profile.save()

        user_profile = user.userprofile
        user_profile.set_instance_privacy_level(PUBLIC)

        eq_(user_profile.vouched_by, voucher.userprofile)

    def test_voucher_nonpublic(self):
        voucher = UserFactory.create(userprofile={'is_vouched': True})
        user = UserFactory.create(
            userprofile={'is_vouched': True,
                         'vouched_by': voucher.userprofile})
        user_profile = user.userprofile
        user_profile.set_instance_privacy_level(PUBLIC)

        eq_(user_profile.vouched_by, None)

    @patch.object(basket, 'lookup_user', autospec=basket.lookup_user)
    def test_lookup_token_registered(self, mock_lookup_user):
        # Lookup token for a user with registered email
        # basket returns response with data, lookup_basket_token returns the token
        user = User(email='fake@example.com')
        profile = UserProfile(user=user)
        mock_lookup_user.return_value = {'status': 'ok', 'token': 'FAKETOKEN'}
        result = profile.lookup_basket_token()
        eq_('FAKETOKEN', result)

    @patch.object(basket, 'lookup_user', autospec=basket.lookup_user)
    def test_lookup_token_unregistered(self, mock_lookup_user):
        # Lookup token for a user with no registered email
        # Basket raises unknown user exception, then lookup-token returns None
        user = User(email='fake@example.com')
        profile = UserProfile(user=user)
        mock_lookup_user.side_effect = \
            basket.BasketException(code=basket.errors.BASKET_UNKNOWN_EMAIL)
        result = profile.lookup_basket_token()
        ok_(result is None)

    @patch.object(basket, 'lookup_user', autospec=basket.lookup_user)
    def test_lookup_token_exceptions(self, mock_lookup_user):
        # If basket raises any exception other than BASKET_UNKNOWN_EMAIL when
        # we call lookup_basket_token, lookup_basket_token passes it up the chain
        class SomeException(Exception):
            pass
        user = User(email='fake@example.com')
        profile = UserProfile(user=user)
        mock_lookup_user.side_effect = SomeException
        with self.assertRaises(SomeException):
            profile.lookup_basket_token()


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
        with patch.object(UserProfile._meta, 'get_all_field_names') as mock_get_all_field_names:
            UserProfile.privacy_fields()
        ok_(mock_get_all_field_names.called)
        # If we call privacy_fields() again, it shouldn't need to compute it all again
        with patch.object(UserProfile._meta, 'get_all_field_names') as mock_get_all_field_names:
            UserProfile.privacy_fields()
        ok_(not mock_get_all_field_names.called)
