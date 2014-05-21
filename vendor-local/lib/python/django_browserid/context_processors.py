# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from functools import partial

from django_browserid import helpers
from django_browserid.forms import BrowserIDForm


def browserid(request):
    """
    Context processor that adds django-browserid helpers to the template
    context.
    """
    form = BrowserIDForm(auto_id=False)
    return {
        'browserid_form': form,  # For custom buttons.
        'browserid_info': partial(helpers.browserid_info, request),
        'browserid_login': helpers.browserid_login,
        'browserid_logout': helpers.browserid_logout,
        'browserid_js': helpers.browserid_js,
        'browserid_css': helpers.browserid_css
    }
