from contextlib import nested
from datetime import datetime

from django.contrib.auth.models import User
from django.test.utils import override_settings

from mock import MagicMock, Mock, call, patch
from nose.tools import ok_
from pyes.exceptions import ElasticSearchException

from mozillians.common.tests import TestCase
from mozillians.groups.tests import GroupFactory
from mozillians.users.managers import PUBLIC
from mozillians.users.models import UserProfile
from mozillians.users.tasks import (_email_basket_managers, index_objects,
                                    remove_incomplete_accounts, unindex_objects,
                                    remove_from_basket_task, update_basket_task)
from mozillians.users.tests import UserFactory


class IncompleteAccountsTests(TestCase):
    """Incomplete accounts removal tests."""

    @patch('mozillians.users.tasks.datetime')
    def test_remove_incomplete_accounts(self, datetime_mock):
        """Test remove incomplete accounts."""
        complete_user = UserFactory.create(
            date_joined=datetime(2012, 01, 01))
        complete_vouched_user = UserFactory.create(
            date_joined=datetime(2013, 01, 01),
            userprofile={'is_vouched': True})
        incomplete_user_not_old = UserFactory.create(
            date_joined=datetime(2013, 01, 01),
            userprofile={'full_name': ''})
        incomplete_user_old = UserFactory.create(
            date_joined=datetime(2012, 01, 01),
            userprofile={'full_name': ''})

        datetime_mock.now.return_value = datetime(2013, 01, 01)

        remove_incomplete_accounts(days=0)
        ok_(User.objects.filter(id=complete_user.id).exists())
        ok_(User.objects.filter(id=complete_vouched_user.id).exists())
        ok_(User.objects.filter(id=incomplete_user_not_old.id).exists())
        ok_(not User.objects.filter(id=incomplete_user_old.id).exists())


@override_settings(ES_DISABLED=False)
class ElasticSearchIndexTests(TestCase):
    @patch('mozillians.users.tasks.get_es')
    def test_index_objects(self, get_es_mock):
        user_1 = UserFactory.create()
        user_2 = UserFactory.create()
        model = MagicMock()
        model.objects.filter.return_value = [
            user_1.userprofile, user_2.userprofile]
        index_objects(
            model, [user_1.userprofile.id, user_2.userprofile.id], False)
        model.objects.assert_has_calls([
            call.filter(id__in=[user_1.userprofile.id, user_2.userprofile.id])])
        model.index.assert_has_calls([
            call(model.extract_document(), bulk=True, id_=user_1.userprofile.id,
                 es=get_es_mock(), public_index=False),
            call(model.extract_document(), bulk=True, id_=user_2.userprofile.id,
                 es=get_es_mock(), public_index=False)])
        model.refresh_index.assert_has_calls([
            call(es=get_es_mock()),
            call(es=get_es_mock())])

    @patch('mozillians.users.tasks.get_es')
    def test_index_objects_public(self, get_es_mock):
        user_1 = UserFactory.create()
        user_2 = UserFactory.create()
        model = MagicMock()
        model.objects.privacy_level().filter.return_value = [
            user_1.userprofile, user_2.userprofile]
        index_objects(
            model, [user_1.userprofile.id, user_2.userprofile.id], True)
        model.objects.assert_has_calls([
            call.filter(id__in=[user_1.userprofile.id, user_2.userprofile.id]),
            call.privacy_level(PUBLIC)])
        model.index.assert_has_calls([
            call(model.extract_document(), bulk=True, id_=user_1.userprofile.id,
                 es=get_es_mock(), public_index=True),
            call(model.extract_document(), bulk=True, id_=user_2.userprofile.id,
                 es=get_es_mock(), public_index=True)])
        model.refresh_index.assert_has_calls([
            call(es=get_es_mock()),
            call(es=get_es_mock())])

    @patch('mozillians.users.tasks.get_es')
    def test_unindex_objects(self, get_es_mock):
        model = MagicMock()
        unindex_objects(model, [1, 2, 3], 'foo')
        ok_(model.unindex.called)
        model.assert_has_calls([
            call.unindex(es=get_es_mock(), public_index='foo', id=1),
            call.unindex(es=get_es_mock(), public_index='foo', id=2),
            call.unindex(es=get_es_mock(), public_index='foo', id=3)])

    def test_unindex_raises_not_found_exception(self):
        exception = ElasticSearchException(
            error=404, status=404, result={'not found': 'not found'})
        model = Mock()
        model.unindex = Mock(side_effect=exception)
        unindex_objects(model, [1, 2, 3], 'foo')


class BasketTests(TestCase):
    @override_settings(BASKET_MANAGERS=False)
    @patch('mozillians.users.tasks.send_mail')
    def test_email_basket_managers_email_not_set(self, send_mail_mock):
        _email_basket_managers('foo', 'bar', 'error')
        ok_(not send_mail_mock.called)

    @override_settings(BASKET_MANAGERS='basket_managers',
                       FROM_NOREPLY='noreply')
    @patch('mozillians.users.tasks.send_mail')
    def test_email_basket_managers(self, send_mail_mock):
        subject = '[Mozillians - ET] Failed to subscribe or update user bar'
        body = """
    Something terrible happened while trying to subscribe user bar from Basket.

    Here is the error message:

    error
    """
        _email_basket_managers('subscribe', 'bar', 'error')
        send_mail_mock.assert_called_with(
            subject, body, 'noreply', 'basket_managers', fail_silently=False)

    @override_settings(BASKET_NEWSLETTER='newsletter')
    @patch('mozillians.users.tasks.BASKET_ENABLED', True)
    def test_update_basket_task_with_token(self):
        user = UserFactory.create(userprofile={'is_vouched': True,
                                               'country': 'gr',
                                               'city': 'athens',
                                               'basket_token': 'token'})
        group = GroupFactory.create(name='Web Development',
                                    curator=user.userprofile)
        GroupFactory.create(name='Marketing', curator=user.userprofile)
        group.add_member(user.userprofile)
        data = {'country': 'gr',
                'city': 'athens',
                'WEB_DEVELOPMENT': 'Y',
                'MARKETING': 'N'}

        with nested(patch('mozillians.users.tasks.basket.subscribe'),
                    patch('mozillians.users.tasks.request')) \
                as (subscribe_mock, request_mock):
            update_basket_task(user.userprofile.id)

        ok_(not subscribe_mock.called)
        request_mock.assert_called_with(
            'post', 'custom_update_phonebook', token='token', data=data)

    @override_settings(BASKET_NEWSLETTER='newsletter')
    @patch('mozillians.users.tasks.BASKET_ENABLED', True)
    @patch('mozillians.users.tasks.request')
    @patch.object(UserProfile, 'lookup_basket_token')
    @patch('mozillians.users.tasks.basket')
    def test_update_basket_task_without_token(self, basket_mock, lookup_token_mock, request_mock):
        lookup_token_mock.return_value = "basket_token"

        user = UserFactory.create(userprofile={'is_vouched': True,
                                               'country': 'gr',
                                               'city': 'athens'})
        group = GroupFactory.create(
            name='Web Development', curator=user.userprofile)
        GroupFactory.create(name='Marketing', curator=user.userprofile)
        group.add_member(user.userprofile)
        data = {'country': 'gr',
                'city': 'athens',
                'WEB_DEVELOPMENT': 'Y',
                'MARKETING': 'N'}

        basket_mock.subscribe.return_value = {}

        update_basket_task(user.userprofile.id)

        basket_mock.subscribe.assert_called_with(
            user.email, 'newsletter', trigger_welcome='N')
        request_mock.assert_called_with(
            'post', 'custom_update_phonebook', token='basket_token', data=data)
        ok_(UserProfile.objects.filter(
            basket_token='basket_token', id=user.userprofile.id).exists())

    @override_settings(BASKET_NEWSLETTER='newsletter')
    @patch('mozillians.users.tasks.BASKET_ENABLED', True)
    @patch('mozillians.users.tasks.basket.unsubscribe')
    def test_remove_from_basket_task(self, unsubscribe_mock):
        user = UserFactory.create(userprofile={'basket_token': 'foo'})
        remove_from_basket_task(user.email, user.userprofile.basket_token)
        unsubscribe_mock.assert_called_with(
            user.userprofile.basket_token, user.email, newsletters='newsletter')

    @override_settings(BASKET_NEWSLETTER='newsletter')
    @patch('mozillians.users.tasks.BASKET_ENABLED', True)
    @patch('mozillians.users.tasks.basket.unsubscribe')
    @patch.object(UserProfile, 'lookup_basket_token')
    def test_remove_from_basket_task_without_token(self, lookup_token_mock, unsubscribe_mock):
        lookup_token_mock.return_value = 'basket_token'
        user = UserFactory.create(userprofile={'basket_token': ''})
        remove_from_basket_task(user.email, user.userprofile.basket_token)
        user = User.objects.get(pk=user.pk)  # refresh data from DB
        unsubscribe_mock.assert_called_with(
            'basket_token', user.email, newsletters='newsletter')
