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

from django.test import TestCase
from django.db.models.sql.where import Constraint, AND, OR

from ldapdb import escape_ldap_filter
from ldapdb.backends.ldap.compiler import where_as_ldap
from ldapdb.models.fields import CharField, IntegerField, ListField
from ldapdb.models.query import WhereNode

class WhereTestCase(TestCase):
    def test_escape(self):
        self.assertEquals(escape_ldap_filter(u'fôöbàr'), u'fôöbàr')
        self.assertEquals(escape_ldap_filter('foo*bar'), 'foo\\2abar')
        self.assertEquals(escape_ldap_filter('foo(bar'), 'foo\\28bar')
        self.assertEquals(escape_ldap_filter('foo)bar'), 'foo\\29bar')
        self.assertEquals(escape_ldap_filter('foo\\bar'), 'foo\\5cbar')
        self.assertEquals(escape_ldap_filter('foo\\bar*wiz'), 'foo\\5cbar\\2awiz')

    def test_char_field_exact(self):
        where = WhereNode()
        where.add((Constraint("cn", "cn", CharField()), 'exact', "test"), AND)
        self.assertEquals(where_as_ldap(where), ("(cn=test)", []))

        where = WhereNode()
        where.add((Constraint("cn", "cn", CharField()), 'exact', "(test)"), AND)
        self.assertEquals(where_as_ldap(where), ("(cn=\\28test\\29)", []))

    def test_char_field_in(self):
        where = WhereNode()
        where.add((Constraint("cn", "cn", CharField()), 'in', ["foo", "bar"]), AND)
        self.assertEquals(where_as_ldap(where), ("(|(cn=foo)(cn=bar))", []))

        where = WhereNode()
        where.add((Constraint("cn", "cn", CharField()), 'in', ["(foo)", "(bar)"]), AND)
        self.assertEquals(where_as_ldap(where), ("(|(cn=\\28foo\\29)(cn=\\28bar\\29))", []))

    def test_char_field_startswith(self):
        where = WhereNode()
        where.add((Constraint("cn", "cn", CharField()), 'startswith', "test"), AND)
        self.assertEquals(where_as_ldap(where), ("(cn=test*)", []))

        where = WhereNode()
        where.add((Constraint("cn", "cn", CharField()), 'startswith', "te*st"), AND)
        self.assertEquals(where_as_ldap(where), ("(cn=te\\2ast*)", []))

    def test_char_field_endswith(self):
        where = WhereNode()
        where.add((Constraint("cn", "cn", CharField()), 'endswith', "test"), AND)
        self.assertEquals(where_as_ldap(where), ("(cn=*test)", []))

        where = WhereNode()
        where.add((Constraint("cn", "cn", CharField()), 'endswith', "te*st"), AND)
        self.assertEquals(where_as_ldap(where), ("(cn=*te\\2ast)", []))

    def test_char_field_contains(self):
        where = WhereNode()
        where.add((Constraint("cn", "cn", CharField()), 'contains', "test"), AND)
        self.assertEquals(where_as_ldap(where), ("(cn=*test*)", []))

        where = WhereNode()
        where.add((Constraint("cn", "cn", CharField()), 'contains', "te*st"), AND)
        self.assertEquals(where_as_ldap(where), ("(cn=*te\\2ast*)", []))

    def test_integer_field(self):
        where = WhereNode()
        where.add((Constraint("uid", "uid", IntegerField()), 'exact', 1), AND)
        self.assertEquals(where_as_ldap(where), ("(uid=1)", []))

        where = WhereNode()
        where.add((Constraint("uid", "uid", IntegerField()), 'gte', 1), AND)
        self.assertEquals(where_as_ldap(where), ("(uid>=1)", []))

        where = WhereNode()
        where.add((Constraint("uid", "uid", IntegerField()), 'lte', 1), AND)
        self.assertEquals(where_as_ldap(where), ("(uid<=1)", []))

    def test_list_field_contains(self):
        where = WhereNode()
        where.add((Constraint("memberUid", "memberUid", ListField()), 'contains', 'foouser'), AND)
        self.assertEquals(where_as_ldap(where), ("(memberUid=foouser)", []))

        where = WhereNode()
        where.add((Constraint("memberUid", "memberUid", ListField()), 'contains', '(foouser)'), AND)
        self.assertEquals(where_as_ldap(where), ("(memberUid=\\28foouser\\29)", []))

    def test_and(self):
        where = WhereNode()
        where.add((Constraint("cn", "cn", CharField()), 'exact', "foo"), AND)
        where.add((Constraint("givenName", "givenName", CharField()), 'exact', "bar"), AND)
        self.assertEquals(where_as_ldap(where), ("(&(cn=foo)(givenName=bar))", []))

    def test_or(self):
        where = WhereNode()
        where.add((Constraint("cn", "cn", CharField()), 'exact', "foo"), AND)
        where.add((Constraint("givenName", "givenName", CharField()), 'exact', "bar"), OR)
        self.assertEquals(where_as_ldap(where), ("(|(cn=foo)(givenName=bar))", []))

