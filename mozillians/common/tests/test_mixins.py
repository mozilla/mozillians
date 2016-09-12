from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import override_settings

import boto

from mock import patch, ANY, MagicMock
from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase
from mozillians.groups.tests import GroupFactory
from mozillians.users.tests import UserFactory


class S3ExportMixinTests(TestCase):
    def test_export_view_get(self):
        user = UserFactory.create(is_superuser=True, is_staff=True)
        export_url = reverse('admin:users_userprofile_export')

        with self.login(user) as client:
            response = client.get(export_url)
            eq_(response.status_code, 200)

    @override_settings(AWS_ACCESS_KEY_ID='foo')
    @override_settings(AWS_SECRET_ACCESS_KEY='bar')
    @override_settings(MOZILLIANS_ADMIN_BUCKET='s3-bucket')
    def test_export_view_post(self):
        user = UserFactory.create(is_superuser=True, is_staff=True)
        export_url = reverse('admin:users_userprofile_export')

        # NDA group required for admin response rendering
        GroupFactory.create(name=settings.NDA_GROUP)

        mock_bucket = MagicMock()
        mock_connection = MagicMock()
        mock_connection.get_bucket.return_value = mock_bucket

        with patch('mozillians.common.mixins.S3ExportMixin.get_export_filename') as mock_filename:
            with patch('mozillians.common.mixins.boto') as mock_boto:
                mock_boto.connect_s3.return_value = mock_connection
                mock_filename.return_value = 'example_filename.format'

                with self.login(user) as client:
                    data = {
                        'file_format': '0'
                    }

                    client.post(export_url, data=data)

                kwargs = {
                    'calling_format': ANY,
                    'aws_access_key_id': 'foo',
                    'aws_secret_access_key': 'bar'
                }
                calling_format = mock_boto.connect_s3.call_args[1]['calling_format']

                mock_boto.connect_s3.assert_called_with(**kwargs)
                ok_(isinstance(calling_format, boto.s3.connection.OrdinaryCallingFormat))
                mock_connection.get_bucket.assert_called_with('s3-bucket')
                mock_bucket.new_key.assert_called_with('example_filename.format')
