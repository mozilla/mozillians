# -*- coding: utf-8 -*-
# 
# django-ldapdb
# Copyright (c) 2009-2011, Bolloré telecom
# All rights reserved.
# 
# See AUTHORS file for a full list of contributors.
# 
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
# 
#     1. Redistributions of source code must retain the above copyright notice, 
#        this list of conditions and the following disclaimer.
#     
#     2. Redistributions in binary form must reproduce the above copyright 
#        notice, this list of conditions and the following disclaimer in the
#        documentation and/or other materials provided with the distribution.
# 
#     3. Neither the name of Bolloré telecom nor the names of its contributors
#        may be used to endorse or promote products derived from this software
#        without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

def is_ldap_model(model):
    # FIXME: there is probably a better check than testing 'base_dn'
    return hasattr(model, 'base_dn')

class Router(object):
    """
    A router to point database operations on LDAP models to the LDAP
    database.

    NOTE: if you have more than one LDAP database, you will need to
    write your own router.
    """

    def __init__(self):
        "Find the name of the LDAP database"
        from django.conf import settings
        self.ldap_alias = None
        for alias, settings_dict in settings.DATABASES.items():
            if settings_dict['ENGINE'] == 'ldapdb.backends.ldap':
                self.ldap_alias = alias
                break

    def allow_syncdb(self, db, model):
        "Do not create tables for LDAP models"
        if is_ldap_model(model):
            return db == self.ldap_alias
        return None

    def db_for_read(self, model, **hints):
        "Point all operations on LDAP models to the LDAP database"
        if is_ldap_model(model):
            return self.ldap_alias
        return None

    def db_for_write(self, model, **hints):
        "Point all operations on LDAP models to the LDAP database"
        if is_ldap_model(model):
            return self.ldap_alias
        return None

