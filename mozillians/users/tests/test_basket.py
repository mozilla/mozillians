from django.conf import settings

from funfactory.urlresolvers import reverse
from mock import patch

from mozillians.common.tests.init import ESTestCase


class BasketTests(ESTestCase):
    """Basket Integration Tests."""
    fake_assertion = 'mrfusionsomereallylongstring'

    @patch('users.tasks.basket.subscribe')
    def test_basket_call_on_vouch(self, mock_obj):
        """Test basket subscribe call on vouch."""
        mock_obj.return_value = {'created': True,
                                 'status': 'ok',
                                 'token': 'test-token'}
        self.pending.userprofile.vouch(self.mozillian.userprofile)
        mock_obj.assert_called_with(self.pending.email,
                                    settings.BASKET_NEWSLETTER,
                                    trigger_welcome='N')

    @patch('users.tasks.request')
    def test_basket_call_on_edit(self, mock_obj):
        data = self.data_privacy_fields.copy()
        data.update({'full_name': 'Foobar', 'username': self.mozillian.username,
                     'country': 'gr'})
        userprofile = self.mozillian.userprofile
        userprofile.basket_token = 'exampleid'
        userprofile.save()
        mock_obj.return_value = {'status': 'ok'}
        self.mozillian_client.post(reverse('profile.edit'), data)
        mock_obj.assert_called_with('post', 'custom_update_phonebook',
                                    token=userprofile.basket_token,
                                    data={'country': 'gr'})

    @patch('users.tasks.basket.unsubscribe')
    def test_remove_from_basket_on_delete(self, mock_obj):
        """Test remove from basket on delete."""
        mock_obj.return_value = {'status': 'ok'}
        userprofile = self.mozillian.userprofile
        userprofile.basket_token = 'exampleid'
        userprofile.save()
        self.mozillian_client.post(reverse('profile.delete'))
        mock_obj.assert_called_with(userprofile.basket_token,
                                    userprofile.user.email,
                                    newsletters=settings.BASKET_NEWSLETTER)
