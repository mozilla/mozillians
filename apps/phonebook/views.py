import logging
log = logging.getLogger('phonebook')
log.addHandler(logging.StreamHandler())
log.setLevel(logging.DEBUG)


from django.http import HttpResponse
from django.http import Http404
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

import django.contrib.auth

from commons.urlresolvers import reverse

import jingo
from tower import ugettext as _

import larper
from larper import models

from . import forms


def profile_uid(request, uniqueIdentifier):
    """
    uniqueIdentifier is a stable, random user id.
    """
    p = models.Person(request)
    person = p.find_by_uniqueIdentifier(uniqueIdentifier)
    # TODO(ozten) API - A pending user gets {'uniqueIdentifier': ['7f3a67u000100']}
    # when they search for others... A Mozillian gets a fuller object
    if 'uid' in person:
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
    vouch_form = None
    person['voucher'] = None

    if 'mozilliansVouchedBy' in person:
        p = models.Person(request)
        voucher_dn = person['mozilliansVouchedBy'][0]
        person['voucher'] = p.find_by_dn(voucher_dn)
    else:
        try:            
            voucher = request.user.ldap_user.attrs['uniqueIdentifier'][0]
            vouch_form = forms.VouchForm(initial=dict(
                    voucher=voucher, 
                    vouchee=person['uniqueIdentifier'][0]))
        except AttributeError, e:
            form = forms.VouchForm()
            log.error(e)
    return jingo.render(request, 'phonebook/profile.html',
                        dict(person=person, vouch_form=vouch_form))


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
    del_form = forms.DeleteForm(
        initial={'uniqueIdentifier': uniqueIdentifier})
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
            # TODO(ozten) Where layers do we let ldap nominclature bleed into?
            if 'givenName' in person:
                first = person['givenName'][0]
            else:
                first = ''
            if 'description' in person:
                bio = person['description'][0]
            else:
                bio = ''
            form = forms.ProfileForm(initial={
                    'first_name': first,
                    'last_name': person['sn'][0],
                    'biography': bio, })

        return jingo.render(request, 'phonebook/edit_profile.html', dict(
                form=form,
                delete_form=del_form,
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
    # TODO push down into larper?
    profile = {
               'cn': display_name,
               'givenName': first_name,
               'sn': last_name,
               'displayName': display_name,
               'description': biography,
               }
    p.update_person(person, profile)


@require_POST
def delete(request):
    form = forms.DeleteForm(request.POST)
    if form.is_valid():
        larper.delete_person(request, form.cleaned_data['uniqueIdentifier'])
        django.contrib.auth.logout(request)
    else:
        log.error("Some funny business...")
    return redirect('home')
        


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
    message = _("Hi, I'm sending you this because I think you should join "
                'mozillians.org, the community directory for Mozilla '
                'contributors like you. You can create a profile for yourself '
                'about what you do in the community as well as search for '
                'other contributors to learn more about them or get in touch. '
                'Check it out.')

    return jingo.render(request, 'phonebook/invite.html')

@require_POST
def vouch(request):    
    form = forms.VouchForm(request.POST)
    if form.is_valid():
        voucher = form.cleaned_data.get('voucher').encode('utf-8')
        vouchee = form.cleaned_data.get('vouchee').encode('utf-8')
        larper.vouch_person(request, voucher, vouchee)
        return redirect(reverse('phonebook.profile_uid', args=[vouchee]))
