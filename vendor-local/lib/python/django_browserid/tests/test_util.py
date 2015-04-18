import json

from mock import Mock, patch
from nose.tools import eq_

from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.utils.functional import lazy

from django_browserid.tests import patch_settings
from django_browserid.util import import_function_from_setting, LazyEncoder


def _lazy_string():
    return 'blah'
lazy_string = lazy(_lazy_string, unicode)()


class TestLazyEncoder(TestCase):
    def test_lazy(self):
        thing = ['foo', lazy_string]
        thing_json = json.dumps(thing, cls=LazyEncoder)
        eq_('["foo", "blah"]', thing_json)


class ImportFunctionFromSettingTests(TestCase):
    def test_no_setting(self):
        """If the setting doesn't exist, raise ImproperlyConfigured."""
        with self.assertRaises(ImproperlyConfigured):
            import_function_from_setting('DOES_NOT_EXIST')

    @patch_settings(TEST_SETTING={})
    def test_invalid_import(self):
        """If the setting isn't a proper string, raise ImproperlyConfigured."""
        with self.assertRaises(ImproperlyConfigured):
            import_function_from_setting('TEST_SETTING')

    @patch('django_browserid.util.import_module')
    @patch_settings(TEST_SETTING='foo.bar.baz')
    def test_failed_import(self, import_module):
        """If there is an error importing the module, raise ImproperlyConfigured."""
        import_module.side_effect = ImportError
        with self.assertRaises(ImproperlyConfigured):
            import_function_from_setting('TEST_SETTING')
        import_module.assert_called_with('foo.bar')

    @patch('django_browserid.util.import_module')
    @patch_settings(TEST_SETTING='foo.bar.baz')
    def test_error_importing(self, import_module):
        """If there is an error importing the module, raise ImproperlyConfigured."""
        import_module.side_effect = ImportError
        with self.assertRaises(ImproperlyConfigured):
            import_function_from_setting('TEST_SETTING')
        import_module.assert_called_with('foo.bar')

    @patch('django_browserid.util.import_module')
    @patch_settings(TEST_SETTING='foo.bar.baz')
    def test_missing_attribute(self, import_module):
        """If the module is imported, but the function isn't found, raise ImproperlyConfigured."""
        import_module.return_value = Mock(spec=[])
        with self.assertRaises(ImproperlyConfigured):
            import_function_from_setting('TEST_SETTING')

    @patch('django_browserid.util.import_module')
    @patch_settings(TEST_SETTING='foo.bar.baz')
    def test_existing_attribute(self, import_module):
        """If the module is imported and has the requested function, return it."""
        module = Mock(spec=['baz'])
        import_module.return_value = module
        self.assertEqual(import_function_from_setting('TEST_SETTING'), module.baz)

