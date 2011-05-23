# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Domesday.
#
# The Initial Developer of the Original Code is
# The Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   The Original Software was written to the Glory of God by 
#   Gervase Markham <written.to.the.glory.of.God@gerv.net>.
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

from django.shortcuts import get_object_or_404, render_to_response
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.db.models import Q

from domesday.models import Person, Account, AccountType

import jingo
import re
import sys
import random
import json

def _fill_in_person(request, p):
        #import pprint
        #pp = pprint.PrettyPrinter(indent=4)
        #pp.pprint(request.POST)
        
        # User data from request
        for field in ('name', 'familyName', 'nickname', 'website', 'blog', 
                      'address', 'locality', 'country', 'phone', 'title',
                      'bio', 'email', 'phoneNumber', 'startyear', 
                      'tshirtsize'):
            # Do any fields need validity checking? Perhaps country and
            # t-shirt size. Do we need to do email validation?
            setattr(p, field, request.POST.get(field, ''))
        
        p.tags = [t.strip() for t in request.POST.get('tags', '').split(",")]
        
        accounts = [{ 'domain': k.split('-', 1)[1], 'userid': v } 
                         for k, v in request.POST.items() 
                         if k.startswith('account-')]
        
        newdomain = request.POST.get('newaccount-domain-manual', '') \
                    or request.POST.get('newaccount-domain', '')
        newid     = request.POST.get('newaccount-userid', '')
        
        if newid and newdomain:
            accounts.append({ 'domain': newdomain, 'userid': newid })
        
        p.accounts = accounts
        
        if 'photo' in request.FILES:
            p.photo = request.FILES['photo'].read()
        

# uid must be specified; host is optional
def _find_person_for_account(domain, userid):
    p = None
    accounts = Account.objects.filter(userid=userid)
    if domain:
        accounts = accounts.filter(domain=domain)
    
    if len(accounts):
        p = accounts[0].owner
        
    return p

def edit(request, pk):
    p = get_object_or_404(Person, pk=pk)
    
    if request.method == "POST":
        _fill_in_person(request, p)
        p.save()
        
    sds = AccountType.as_dict()
    
    return jingo.render(request, 'domesday/edit.html', {'p': p, 'sds': sds})

def new(request):
    if request.method == "POST":
        # XXX We need proper UID allocation here
        uid = random.randrange(0, 1000000)
        p = Person(uid=uid)
        _fill_in_person(request, p)
        p.save()
        
        # XXX Need to remove URL dependency
        return HttpResponseRedirect("/en-US/edit/" + str(p.uid))
    else:
        # Form to fill in for a new person
        sds = AccountType.objects.all()
        return jingo.render(request, 'domesday/edit.html', 
                            {'p': None, 'sds': sds})
        
def view(request, pk):
    p = get_object_or_404(Person, pk=pk)
    # Need cross-site headers for JSON? Drop privileges?
    format = request.GET.get('format', 'html')
    if format == 'json':
        jp = {
            "startIndex": 1,
            "itemsPerPage": 1,
            "totalResults": 1,
            "entry": [p.json_struct()]
        }
        return HttpResponse(json.dumps(jp), mimetype="application/json")
    else:
        return jingo.render(request, 'domesday/view.%s' % format, {'p': p})

def photo(request, pk):
    p = get_object_or_404(Person, pk=pk)
    return HttpResponse(p.photo, mimetype="image/jpeg")

def search(request):
    if len(request.GET) == 0:
        sds = AccountType.objects.all()
        return jingo.render(request, 'domesday/search.html', {'sds': sds})
    else:
        query = request.GET['q']
        sname = request.GET['sname']
        ps = None
        
        if not sname:
            # Search everything - email, then other accounts, then nickname
            ps = Person.objects.filter(email=query)
            if not ps:
                ps = _find_person_for_account(None, query)
            if not ps:
                ps = Person.objects.filter(nickname=query)
        elif sname == 'email':
            ps = Person.objects.filter(email=query)
        elif sname == "nickname":
            ps = Person.objects.filter(nickname=query)
        else:
            ps = _find_person_for_account(sname, query)
        
        # XXX need view URL to support None, then this will be cleaner
        if ps:
            p = ps.get()
            # XXX Need to remove URL dependency
            return HttpResponseRedirect("/en-US/view/" + str(p.uid))
        else:
            return jingo.render(request, 'domesday/view.html', {'p': None})

def test(request):
    p = get_object_or_404(Person, pk=1)
    return render_to_response('domesday/test.html', {'p': p})

