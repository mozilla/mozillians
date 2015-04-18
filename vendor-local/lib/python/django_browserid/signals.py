# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from django.dispatch import Signal


user_created = Signal(providing_args=['user'])
"""
Signal triggered when a user is automatically created during authentication.

:param sender:
    The function that created the user instance.

:param user:
    The user instance that was created.
"""
