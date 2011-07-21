import logging
log = logging.getLogger('phonebook')
log.addHandler(logging.StreamHandler())
log.setLevel(logging.DEBUG)


from django.http import HttpResponse
from django.http import Http404
from django.shortcuts import redirect

import jingo

from larper import models

from . import forms


def profile_uid(request, uniqueIdentifier):
    """
    uniqueIdentifier is a stable, random user id.
    """
    p = models.Person(request)
    person = p.find_by_uniqueIdentifier(uniqueIdentifier)
    if person:
        log.error("Person found %s " % person)
        return _profile(request, person)
    else:
        raise Http404


def profile_nickname(request, nickname):
    """ 
    This is probably post 1.0, but we could provide
    a nicer url if we used let the user opt-in to
    a Mozillians nickname (pre-populated from their
    IRC nickname)
    """
    person = do_some_magic(nickname)
    return _profile(request, person)


def _profile(request, person):
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
        if request.user.is_authenticated():
            user = models.Person(request) 
            people = user.search(query)
        
    return jingo.render(request, 'phonebook/search.html',
                        dict(people=people))


def photo(request, uniqueIdentifier):
    user = models.Person(request) 
    person = user.find_by_uniqueIdentifier(uniqueIdentifier)
    if person and 'jpegPhoto' in person:
        return HttpResponse(person['jpegPhoto'][0], mimetype="image/jpeg")
    else:
        return redirect('/media/img/unknown.png')


def invite(request):
    return jingo.render(request, 'phonebook/invite.html')
