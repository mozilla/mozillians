# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from django.db import models

try:
    from django.contrib.auth.models import AbstractBaseUser
except ImportError:
    AbstractBaseUser = object


class CustomUser(AbstractBaseUser):
    USERNAME_FIELD = 'email'

    email = models.EmailField(unique=True, db_index=True)

    def get_full_name(self):
        return self.email

    def get_short_name(self):
        return self.email
