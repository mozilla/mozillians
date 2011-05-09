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
        
        p.tags = request.POST.get('tags', '').split(", ")
        
        accounts = dict([(k.split('-', 1)[1], v) 
                         for k, v in request.POST.items() 
                         if k.startswith('account-')])
        
        newdomain = request.POST.get('newaccount-domain-manual', '') \
                    or request.POST.get('newaccount-domain', '')
        newid     = request.POST.get('newaccount-userid', '')
        
        if newid and newdomain:
            accounts[newdomain] = newid
        
        p.accounts = accounts
        
        # p.photo = request.POST["photo"]
        

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

