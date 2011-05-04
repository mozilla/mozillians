from django.shortcuts import get_object_or_404, render_to_response
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.db.models import Q

from domesday.models import Person, ServiceDefinition

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
        # Trying to do this the obvious, sensible way results in:
        # "'Person' object does not support item assignment"

        #for field in (vars(p)):
        #    if field in request.POST:
        #        print >> sys.stderr, field
        #        p.setattr(field, request.POST[field])
        #        print >> sys.stderr, "Field value: ", p[field]
        
        p.givenName = request.POST["givenname"]
        p.familyName = request.POST["familyname"] or "X"
        p.nickname = request.POST["nickname"]
        p.website = request.POST["website"]
        p.blog = request.POST["blog"]
        p.locality = request.POST["locality"]
        p.country = request.POST["country"]
        p.phone = request.POST["phone"]
        p.title = request.POST["title"]
        
        # p.tags = request.POST["tags"].split(", ")
        
        p.address = request.POST["address"]
        
        p.bio = request.POST["bio"]
        # p.photo = request.POST["photo"]
        p.email = request.POST["email"]

        p.nickname = request.POST["nickname"]
        p.country = request.POST["country"]
        p.phoneNumber = request.POST["phone"]
        p.startyear = request.POST["startyear"]
        p.tshirtsize = request.POST["tshirtsize"]

        p.name = p.givenName + " " + p.familyName
        p.cn = p.name
    
def edit(request, pk):
    p = get_object_or_404(Person, pk=pk)
    
    if request.method == "POST":
        _fill_in_person(request, p)
        p.save()
        
    sds = ServiceDefinition.objects.all()
    
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
        sds = ServiceDefinition.objects.all()
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
        return jingo.render(request, 'domesday/view.html', {'p': p})

def photo(request, pk):
    p = get_object_or_404(Person, pk=pk)
    return HttpResponse(p.photo, mimetype="image/jpeg")

def search(request):
    if len(request.GET) == 0:
        sds = ServiceDefinition.objects.all()
        return jingo.render(request, 'domesday/search.html', {'sds': sds})
    else:
        query = request.GET['q']
        ps = Person.objects.filter(Q(email=query) | Q(nickname=query))
        if (len(ps)):
            p = ps[0]
        else:
            p = None
        return jingo.render(request, 'domesday/view.html', {'p': p})

def test(request):
    p = get_object_or_404(Person, pk=1)
    return render_to_response('domesday/test.html', {'p': p})

