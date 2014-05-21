# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import json

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import Promise
from django.utils.encoding import force_unicode
from django.utils.importlib import import_module


class LazyEncoder(json.JSONEncoder):
    """
    JSONEncoder that turns Promises into unicode strings to support functions
    like ugettext_lazy and reverse_lazy.
    """
    def default(self, obj):
        if isinstance(obj, Promise):
            return force_unicode(obj)
        return super(LazyEncoder, self).default(obj)


def import_function_from_setting(setting):
    """
    Attempt to load a function from a module as specified by a setting.

    :raises:
        ImproperlyConfigured if anything goes wrong.
    """
    try:
        path = getattr(settings, setting)
    except AttributeError as e:
        raise ImproperlyConfigured('Setting {0} not found.'.format(setting))

    try:
        i = path.rfind('.')
        module, attr = path[:i], path[i + 1:]
    except AttributeError as e:
        raise ImproperlyConfigured('Setting {0} should be an import path.'.format(setting))

    try:
        mod = import_module(module)
    except ImportError as e:
        raise ImproperlyConfigured('Error importing `{0}` function: {1}'.format(path, e))

    try:
        return getattr(mod, attr)
    except AttributeError as e:
        raise ImproperlyConfigured('Module {0} does not define a {1} function.'
                                   .format(module, attr))


# Attempt to use staticfiles_storage.url to retrieve static file URLs.
# If it can't be found (Django 1.3), default to prepending settings.STATIC_URL
# to the given path.
try:
    from django.contrib.staticfiles.storage import staticfiles_storage
    static_url = staticfiles_storage.url
except ImportError:
    from django.conf import settings

    def static_url(path):
        """Return a public URL for the given static file path."""
        return ''.join([settings.STATIC_URL, path])

