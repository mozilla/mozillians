from datetime import datetime

from django.contrib.auth.models import User
from django.test.utils import override_settings

from basket.base import BasketException
from celery.exceptions import Retry
from elasticsearch.exceptions import NotFoundError
from mock import MagicMock, Mock, call, patch
from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase
from mozillians.users.managers import PUBLIC
from mozillians.users.tasks import (index_objects, lookup_user_task, remove_incomplete_accounts,
                                    subscribe_user_task, subscribe_user_to_basket,
                                    unindex_objects, unsubscribe_from_basket_task,
                                    unsubscribe_user_task, update_email_in_basket)
from mozillians.users.tests import UserFactory


class IncompleteAccountsTests(TestCase):
    """Incomplete accounts removal tests."""

    @patch('mozillians.users.tasks.datetime')
    def test_remove_incomplete_accounts(self, datetime_mock):
        """Test remove incomplete accounts."""
        complete_user = UserFactory.create(vouched=False,
                                           date_joined=datetime(2012, 01, 01))
        complete_vouched_user = UserFactory.create(date_joined=datetime(2013, 01, 01))
        incomplete_user_not_old = UserFactory.create(date_joined=datetime(2013, 01, 01),
                                                     userprofile={'full_name': ''})
        incomplete_user_old = UserFactory.create(date_joined=datetime(2012, 01, 01),
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
        mapping_type = MagicMock()
        model = MagicMock()
        mapping_type.get_model.return_value = model
        model.objects.filter.return_value = [user_1.userprofile,
                                             user_2.userprofile]
        mapping_type.extract_document.return_value = 'foo'
        index_objects(mapping_type,
                      [user_1.userprofile.id, user_2.userprofile.id],
                      public_index=False)
        mapping_type.bulk_index.assert_has_calls([
            call(['foo', 'foo'], id_field='id', es=get_es_mock(),
                 index=mapping_type.get_index(False))])

    @patch('mozillians.users.tasks.get_es')
    def test_index_objects_public(self, get_es_mock):
        user_1 = UserFactory.create()
        user_2 = UserFactory.create()
        mapping_type = MagicMock()
        model = MagicMock()
        mapping_type.get_model.return_value = model
        qs = model.objects.filter().public_indexable().privacy_level
        qs.return_value = [user_1.userprofile, user_2.userprofile]
        mapping_type.extract_document.return_value = 'foo'
        index_objects(mapping_type,
                      [user_1.userprofile.id, user_2.userprofile.id],
                      public_index=True)

        model.objects.assert_has_calls([
            call.filter(id__in=(user_1.userprofile.id, user_2.userprofile.id)),
            call.filter().public_indexable(),
            call.filter().public_indexable().privacy_level(PUBLIC),
        ])
        mapping_type.bulk_index.assert_has_calls([
            call(['foo', 'foo'], id_field='id', es=get_es_mock(),
                 index=mapping_type.get_index(True))])

    @patch('mozillians.users.tasks.get_es')
    def test_unindex_objects(self, get_es_mock):
        mapping_type = MagicMock()
        unindex_objects(mapping_type, [1, 2, 3], 'foo')
        ok_(mapping_type.unindex.called)
        mapping_type.assert_has_calls([
            call.unindex(1, es=get_es_mock(), public_index='foo'),
            call.unindex(2, es=get_es_mock(), public_index='foo'),
            call.unindex(3, es=get_es_mock(), public_index='foo')])

    def test_unindex_raises_not_found_exception(self):
        exception = NotFoundError(404, {'not found': 'not found '}, {'foo': 'foo'})
        mapping_type = Mock()
        mapping_type.unindex(side_effect=exception)
        unindex_objects(mapping_type, [1, 2, 3], 'foo')


class BasketTests(TestCase):

    @override_settings(CELERY_ALWAYS_EAGER=True)
    @patch('mozillians.users.tasks.BASKET_ENABLED', True)
    @patch('mozillians.users.tasks.waffle.switch_is_active')
    @patch('mozillians.users.tasks.unsubscribe_user_task')
    @patch('mozillians.users.tasks.subscribe_user_task')
    @patch('mozillians.users.tasks.lookup_user_task')
    @patch('mozillians.users.tasks.basket')
    def test_change_email(self, basket_mock, lookup_mock, subscribe_mock, unsubscribe_mock,
                          switch_is_active_mock):

        # Create a new user
        old_email = 'foo@example.com'
        # We need vouched=False in order to avoid triggering a basket_update through signals.
        user = UserFactory.create(email=old_email, vouched=False)
        new_email = 'bar@example.com'

        # Enable basket.
        switch_is_active_mock.return_value = True

        # Mock all the calls to basket.
        basket_mock.lookup_user.return_value = {
            'email': old_email,  # the old value
            'newsletters': ['foo', 'bar']
        }
        basket_mock.unsubscribe.return_value = {
            'result': 'ok',
        }
        basket_mock.subscribe.return_value = {
            'token': 'new token',
        }

        lookup_mock.reset_mock()
        subscribe_mock.reset_mock()
        unsubscribe_mock.reset_mock()

        # When a user's email is changed, their old email is unsubscribed
        # from all newsletters related to mozillians.org and their new email is subscribed to them.
        update_email_in_basket(user.email, new_email)

        # Verify subtask calls and call count
        ok_(lookup_mock.subtask.called)
        eq_(lookup_mock.subtask.call_count, 1)
        ok_(subscribe_mock.subtask.called)
        eq_(subscribe_mock.subtask.call_count, 1)
        ok_(unsubscribe_mock.subtask.called)
        eq_(unsubscribe_mock.subtask.call_count, 1)

        # Verify call arguments
        lookup_mock.subtask.assert_called_with((user.email,))
        unsubscribe_mock.subtask.called_with(({'token': 'new token',
                                               'email': 'foo@example.com',
                                               'newsletters': ['foo', 'bar']},))
        subscribe_mock.subtask.called_with(('bar@example.com',))

    @patch('mozillians.users.tasks.waffle.switch_is_active')
    @patch('mozillians.users.tasks.unsubscribe_user_task')
    @patch('mozillians.users.tasks.lookup_user_task')
    @patch('mozillians.users.tasks.basket')
    def test_unsubscribe_from_basket_task(self, basket_mock, lookup_mock, unsubscribe_mock,
                                          switch_is_active_mock):
        switch_is_active_mock.return_value = True
        user = UserFactory.create(email='foo@example.com')
        basket_mock.lookup_user.return_value = {
            'email': user.email,  # the old value
            'token': 'token',
            'newsletters': ['foo', 'bar']
        }

        lookup_mock.reset_mock()
        unsubscribe_mock.reset_mock()

        with patch('mozillians.users.tasks.BASKET_ENABLED', True):
            unsubscribe_from_basket_task(user.email, ['foo'])
        eq_(lookup_mock.subtask.call_count, 1)
        eq_(unsubscribe_mock.subtask.call_count, 1)
        lookup_mock.subtask.assert_called_with((user.email,))
        unsubscribe_mock.subtask.called_with((['foo'],))

    @override_settings(CELERY_ALWAYS_EAGER=True)
    @patch('mozillians.users.tasks.BASKET_ENABLED', True)
    @patch('mozillians.users.tasks.waffle.switch_is_active')
    @patch('mozillians.users.tasks.subscribe_user_task.subtask')
    @patch('mozillians.users.tasks.lookup_user_task.subtask')
    def test_subscribe_no_newsletters(self, lookup_mock, subscribe_mock, switch_is_active_mock):
        switch_is_active_mock.return_value = True
        user = UserFactory.create(vouched=False)
        result = subscribe_user_to_basket.delay(user.userprofile.pk)
        ok_(lookup_mock.called)
        ok_(not subscribe_mock.called)
        ok_(not result.get())

    @patch('mozillians.users.tasks.basket.lookup_user')
    def test_lookup_task_user_not_found(self, lookup_mock):

        lookup_mock.side_effect = BasketException(u'User not found')
        result = lookup_user_task(email='foo@example.com')
        eq_(result, {})

    @patch('mozillians.users.tasks.lookup_user_task.retry')
    @patch('mozillians.users.tasks.basket.lookup_user')
    def test_lookup_task_basket_error(self, lookup_mock, retry_mock):

        exc = BasketException(u'Error error error')
        lookup_mock.side_effect = [exc, None]
        retry_mock.side_effect = Retry
        with self.assertRaises(Retry):
            lookup_user_task(email='foo@example.com')
        retry_mock.called_with(exc)

    def test_subscribe_user_task_no_result_no_email(self):
        ok_(not subscribe_user_task(result={}, email=''))

    @patch('mozillians.users.tasks.basket.subscribe')
    def test_subscribe_user_task_no_email_no_newsletters(self, subscribe_mock):
        result = {
            'status': 'ok',
            'newsletters': ['foo', 'bar', 'mozilla-phone'],
            'email': 'result_email@example.com'
        }

        subscribe_user_task(result=result, email=None)
        subscribe_mock.assert_called_with('result_email@example.com', ['mozilla-phone'],
                                          sync='N', trigger_welcome='N',
                                          api_key='basket_api_key')

    @patch('mozillians.users.tasks.basket.subscribe')
    def test_subscribe_user_task_no_newsletters(self, subscribe_mock):
        result = {
            'status': 'ok',
            'newsletters': ['foo', 'bar'],
            'email': 'result_email@example.com'
        }

        subscribe_user_task(result=result, email='foo@xample.com')
        subscribe_mock.assert_not_called()

    @patch('mozillians.users.tasks.basket.subscribe')
    def test_subscribe_user_task(self, subscribe_mock):
        result = {
            'status': 'ok',
            'newsletters': ['foo', 'bar'],
            'email': 'result_email@example.com'
        }
        kwargs = {
            'result': result,
            'email': 'foo@example.com',
            'newsletters': ['foobar', 'foo']
        }
        subscribe_user_task(**kwargs)
        subscribe_mock.assert_called_with('foo@example.com', ['foobar'],
                                          sync='N', trigger_welcome='N',
                                          api_key='basket_api_key')

    @patch('mozillians.users.tasks.basket.subscribe')
    def test_subscribe_user_task_no_result(self, subscribe_mock):
        kwargs = {
            'result': {'status': 'error',
                       'desc': u'User not found'},
            'email': 'foo@example.com',
            'newsletters': ['mozilla-phone']
        }
        subscribe_user_task(**kwargs)
        subscribe_mock.assert_called_with('foo@example.com', ['mozilla-phone'],
                                          sync='N', trigger_welcome='N',
                                          api_key='basket_api_key')

    @patch('mozillians.users.tasks.subscribe_user_task.retry')
    @patch('mozillians.users.tasks.basket.subscribe')
    def test_subscribe_user_basket_error(self, subscribe_mock, retry_mock):
        result = {
            'status': 'ok',
            'newsletters': ['foo', 'bar'],
            'email': 'result_email@example.com'
        }
        kwargs = {
            'result': result,
            'email': 'foo@example.com',
            'newsletters': ['foobar', 'foo']
        }

        exc = BasketException(u'Error error error')
        subscribe_mock.side_effect = [exc, None]
        retry_mock.side_effect = Retry
        with self.assertRaises(Retry):
            subscribe_user_task(**kwargs)
        retry_mock.called_with(exc)

    def test_unsubscribe_user_no_result(self):
        ok_(not unsubscribe_user_task(result={}))

    @patch('mozillians.users.tasks.basket.unsubscribe')
    def test_unsubscribe_user_task_success_no_newsletters(self, unsubscribe_mock):
        result = {
            'status': 'ok',
            'newsletters': ['foo', 'bar', 'mozilla-phone'],
            'email': 'result_email@example.com',
            'token': 'token'
        }

        unsubscribe_user_task(result)
        unsubscribe_mock.assert_called_with(token='token', email='result_email@example.com',
                                            newsletters=['mozilla-phone'], optout=False)

    @patch('mozillians.users.tasks.basket.unsubscribe')
    def test_unsubscribe_user_task_success(self, unsubscribe_mock):
        result = {
            'status': 'ok',
            'newsletters': ['foo', 'bar', 'foobar'],
            'email': 'result_email@example.com',
            'token': 'token'
        }

        unsubscribe_user_task(result, newsletters=['foo', 'bar'])
        unsubscribe_mock.assert_called_with(token='token', email='result_email@example.com',
                                            newsletters=['foo', 'bar'], optout=False)

    @patch('mozillians.users.tasks.unsubscribe_user_task.retry')
    @patch('mozillians.users.tasks.basket.unsubscribe')
    def test_unsubscribe_user_basket_error(self, unsubscribe_mock, retry_mock):
        result = {
            'status': 'ok',
            'newsletters': ['foo', 'bar'],
            'email': 'result_email@example.com',
            'token': 'token'
        }

        exc = BasketException(u'Error error error')
        unsubscribe_mock.side_effect = [exc, None]
        retry_mock.side_effect = Retry
        with self.assertRaises(Retry):
            unsubscribe_user_task(result, newsletters=['foo', 'bar'])
        retry_mock.called_with(exc)
