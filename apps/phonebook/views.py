import logging
log = logging.getLogger('phonebook')
log.addHandler(logging.StreamHandler())
log.setLevel(logging.DEBUG)

from django.shortcuts import get_object_or_404
from django.http import HttpResponse

import jingo

from larper import models

from . import forms
from . import models


def profile_uid(request, userid):
    return profile(request, userid)


def profile_nickname(request, nickname):
    return profile(request, nickname)


def profile(request, person):
    return jingo.render(request, 'phonebook/profile.html',
                        dict(person=person))


def edit_profile(request, person):
    return jingo.render(request, 'phonebook/edit_profile.html')


def search(request):
    people = []
    form = forms.SearchForm(request.GET)
    if form.is_valid():
        query = form.cleaned_data.get('q', '')
        log.error("Search Query: %s" % query)
        people = models.Person.objects.filter(email__startswith=query)
        log.error("Search Results: %s" % str(people))
        # TODO(ozten) starting to replace django-ldapdb with larper
        if request.user.is_authenticated():
            user = models.Person(request) 
            user.search('david')
        
    return jingo.render(request, 'phonebook/search.html',
                        dict(people=people))


def photo(request, stable_id):
    p = get_object_or_404(models.Person, stable_uid=stable_id)
    return HttpResponse(p.photo, mimetype="image/jpeg")


def invite(request):
    return jingo.render(request, 'phonebook/invite.html')
