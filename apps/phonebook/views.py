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


def edit_profile(request, uniqueIdentifier):
    """ Why does this and edit_new_profile accept a uniqueIdentifier
    Instead of just using the request.user object?

    LDAP's ACL owns if the current user can edit the user or not.
    We get a rich admin screen for free, for LDAPAdmin users.
    """
    return _edit_profile(request, uniqueIdentifier, False)


def edit_new_profile(request, uniqueIdentifier):
    return _edit_profile(request, uniqueIdentifier, True)


def _edit_profile(request, uniqueIdentifier, new_account):
    p = models.Person(request)
    person = p.find_by_uniqueIdentifier(uniqueIdentifier)
    if person:
        if request.method == 'POST':
            form = forms.ProfileForm(request.POST)
            if form.is_valid():
                _update_profile(p, person, form)
                if new_account:
                    return redirect('confirm_register')
                else:
                    return redirect('phonebook.profile_uid', uniqueIdentifier)
        else:
            # TODO(ozten) what is the first name ldap field?
            # TODO(ozten) Where layers do we let ldap nominclature bleed into?
            if 'displayName' in person:
                first = person['displayName'][0].split()[0]
            else:
                first = ''
            if 'biography' in person:
                bio = person['biography']
            else:
                bio = ''
            form = forms.ProfileForm(initial={
                    'first_name': first,
                    'last_name': person['sn'][0],
                    'biography': bio, })

        return jingo.render(request, 'phonebook/edit_profile.html', dict(
                form=form,
                person=person,
                registration_flow=new_account,
                ))
    else:
        raise Http404


def _update_profile(p, person, form):
    """ TODO DRY with users/views.py """

    # Optional
    first_name = form.cleaned_data['first_name'].encode('utf-8') or ""
    last_name = form.cleaned_data['last_name'].encode('utf-8')
    biography = form.cleaned_data['biography'].encode('utf-8')

    display_name = ("%s %s" % (first_name, last_name)).encode('utf-8')

    profile = {
               #'objectclass': ['inetOrgPerson','person','mozilliansPerson'],
               'cn': display_name,
               #'givenName': first_name,
               'sn': last_name,
               'displayName': display_name,
               #'userPassword': password,
               #'uid': email,
               #'mail': email,
               }
    p.update_person(person, profile)


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
    # TODO: actually send this
    subject = _('Become a Mozillian')
    message = _('Hi, I'm sending you this because I think you should join '
                'mozillians.org, the community directory for Mozilla '
                'contributors like you. You can create a profile for yourself '
                'about what you do in the community as well as search for '
                'other contributors to learn more about them or get in touch. '
                'Check it out.')

    return jingo.render(request, 'phonebook/invite.html')
