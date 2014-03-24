from datetime import datetime

from django.contrib.auth.models import User
from django.test.utils import override_settings

from mock import MagicMock, Mock, call, patch
from nose.tools import eq_, ok_
from pyes.exceptions import ElasticSearchException

from mozillians.common.tests import TestCase
from mozillians.groups.tests import GroupFactory
from mozillians.users.managers import PUBLIC
from mozillians.users.models import UserProfile
from mozillians.users.tasks import (_email_basket_managers, index_objects,
                                    remove_incomplete_accounts, unindex_objects,
                                    remove_from_basket_task)
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
    @patch('mozillians.users.tasks.basket')
    def test_update_basket_task(self, mock_basket):
        # When a user is created or added to a group, the appropriate
        # calls to update basket are made
        email = 'foo@example.com'
        token = 'footoken'
        mock_basket.lookup_user.return_value = {
            'email': email,
        }
        mock_basket.subscribe.return_value = {
            'token': token,
        }
        user = UserFactory.create(
            email=email,
            userprofile={'is_vouched': True,
                         'country': 'gr',
                         'city': 'athens'})
        mock_basket.subscribe.reset_mock()  # forget that subscribe was called
        group = GroupFactory.create(name='Web Development',
                                    curator=user.userprofile)
        GroupFactory.create(name='Marketing', curator=user.userprofile)
        data = {'country': 'gr',
                'city': 'athens',
                'WEB_DEVELOPMENT': 'Y',
                'MARKETING': 'N'}

        group.add_member(user.userprofile)

        # We just added a group, we should not need to subscribe anything
        ok_(not mock_basket.subscribe.called)
        # But we do need to update their phonebook record
        mock_basket.request.assert_called_with(
            'post', 'custom_update_phonebook', token=token, data=data)

    @override_settings(BASKET_NEWSLETTER='newsletter')
    @patch('mozillians.users.tasks.BASKET_ENABLED', True)
    @patch('mozillians.users.tasks.basket')
    def test_change_email(self, mock_basket):
        # When a user's email is changed, their old email is unsubscribed
        # from all newsletters and their new email is subscribed to them.

        # Create a new user
        email = 'foo@example.com'
        token = 'first token'
        mock_basket.lookup_user.return_value = {
            'email': email,  # the old value
            'token': token,
            'newsletters': ['foo', 'bar']
        }
        mock_basket.subscribe.return_value = {
            'token': token,
        }
        user = UserFactory.create(
            email=email,
            userprofile={'is_vouched': True,
                         'country': 'gr',
                         'city': 'athens'})
        up = UserProfile.objects.get(pk=user.userprofile.pk)
        eq_(token, up.basket_token)

        new_email = 'bar@example.com'
        new_token = 'NEW token'
        mock_basket.subscribe.return_value = {
            'token': new_token,
        }
        user.email = new_email
        user.save()
        mock_basket.lookup_user.assert_called_with(token=token)
        mock_basket.unsubscribe.assert_called_with(
            token=token, email=email, optout='Y'
        )
        mock_basket.subscribe.assert_called_with(
            new_email,
            ['foo', 'bar'],
            trigger_welcome='N',
            sync='Y'
        )
        up = UserProfile.objects.get(pk=user.userprofile.pk)
        eq_(new_token, up.basket_token)

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
    @patch('mozillians.users.tasks.basket')
    @patch.object(UserProfile, 'lookup_basket_token')
    def test_remove_from_basket_task_without_token(self, lookup_token_mock, basket_mock):
        lookup_token_mock.return_value = 'basket_token'
        basket_mock.lookup_user.return_value = {'token': 'basket_token'}
        user = UserFactory.create(userprofile={'basket_token': ''})
        remove_from_basket_task(user.email, user.userprofile.basket_token)
        user = User.objects.get(pk=user.pk)  # refresh data from DB
        basket_mock.unsubscribe.assert_called_with(
            'basket_token', user.email, newsletters='newsletter')
