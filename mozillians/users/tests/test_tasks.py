from django.contrib.auth.models import User
from django.test.utils import override_settings

from mock import MagicMock, Mock, call, patch
from nose.tools import ok_
from pyes.exceptions import ElasticSearchException

from mozillians.common.tests import TestCase
from mozillians.users.tests import UserFactory
from mozillians.users.tasks import (index_objects, remove_incomplete_accounts,
                                    unindex_objects)


class IncompleteAccountsTests(TestCase):
    """Incomplete accounts removal tests."""

    def test_remove_incomplete_accounts(self):
        """Test remove incomplete accounts."""
        complete_user = UserFactory.create()
        complete_vouched_user = UserFactory.create(
            userprofile={'is_vouched': True})
        incomplete_user = UserFactory.create(userprofile={'full_name': ''})
        remove_incomplete_accounts(days=0)
        ok_(User.objects.filter(id=complete_user.id).exists())
        ok_(User.objects.filter(id=complete_vouched_user.id).exists())
        ok_(not User.objects.filter(id=incomplete_user.id).exists())


@override_settings(ES_DISABLED=False)
class ElasticSearchIndexTests(TestCase):
    @patch('mozillians.users.tasks.get_es')
    def test_index_objects(self, get_es_mock):
        user_1 = UserFactory.create()
        user_2 = UserFactory.create()
        model = MagicMock()
        model.objects.filter.return_value = [
            user_1.userprofile, user_2.userprofile]
        index_objects(model, [1, 2], False)
        # from nose.tools import set_trace
        # set_trace()
        model.assert_has_calls([
            call.objects.filter(id__in=[1, 2]),
            call.extract_document(1, user_1.userprofile),
            call.index(model.extract_document(), bulk=True, id_=1,
                       es=get_es_mock(), public_index=False),
            call.refresh_index(es=get_es_mock()),
            call.extract_document(2, user_2.userprofile),
            call.index(model.extract_document(), bulk=True, id_=2,
                       es=get_es_mock(), public_index=False),
            call.refresh_index(es=get_es_mock())])


    def test_index_objects_public(self):
        pass

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
        unindex_objects(model, [1,2,3], 'foo')


class BasketTests(TestCase):
    pass
