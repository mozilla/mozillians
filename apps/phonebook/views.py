from functools import wraps
from ldap import SIZELIMIT_EXCEEDED

import django.contrib.auth
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.http import (Http404, HttpResponse, HttpResponseRedirect,
                         HttpResponseForbidden)
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

import jingo
from tower import ugettext as _

import commonware.log
from funfactory.urlresolvers import reverse
from funfactory.utils import absolutify
from larper import UserSession, AdminSession, NO_SUCH_PERSON
from larper import MOZILLA_IRC_SERVICE_URI
from phonebook import forms
from phonebook.models import Invite

log = commonware.log.getLogger('m.phonebook')

BAD_VOUCHER = 'Unknown Voucher'


def vouch_required(f):
    """
    If a user is not vouched they get a 403.
    """
    @login_required
    @wraps(f)
    def wrapped(request, *args, **kwargs):
        if request.user.is_vouched():
            return f(request, *args, **kwargs)
        else:
            log.warning('vouch_required forbidding access')
            return HttpResponseForbidden(_('You must be vouched to do this.'))

    return wrapped


@never_cache
@login_required
def profile_uid(request, unique_id):
    """
    View a profile by unique_id, which is a stable,
    random user id.
    """
    needs_master = (request.user.unique_id == unique_id)

    ldap = UserSession.connect(request)
    log.warning('profile_uid [%s]' % unique_id)
    try:
        # Stale data okay when viewing others
        person = ldap.get_by_unique_id(unique_id, needs_master)
        if person.last_name:
            return _profile(request, person, needs_master)
    except NO_SUCH_PERSON:
        log.warning('profile_uid Sending 404 for [%s]' % unique_id)
        raise Http404


def profile_nickname(request, nickname):
    """
    TODO
    This is probably post 1.0, but we could provide
    a nicer url if we used let the user opt-in to
    a Mozillians nickname (pre-populated from their
    IRC nickname)
    """
    pass
    # return _profile(request, person)


def _profile(request, person, use_master):
    vouch_form = None
    ldap = UserSession.connect(request)

    if person.voucher_unique_id:
        try:
            # Stale data okay
            person.voucher = ldap.get_by_unique_id(person.voucher_unique_id)
        except NO_SUCH_PERSON:
            # Bug#688788 Invalid voucher is okay
            person.voucher = BAD_VOUCHER
    elif request.user.unique_id != person.unique_id:
        voucher = request.user.unique_id
        vouch_form = forms.VouchForm(initial=dict(
                voucher=voucher,
                vouchee=person.unique_id))

    services = ldap.profile_service_ids(person.unique_id, use_master)
    person.irc_nickname = None
    if MOZILLA_IRC_SERVICE_URI in services:
        person.irc_nickname = services[MOZILLA_IRC_SERVICE_URI]
        del services[MOZILLA_IRC_SERVICE_URI]

    data = dict(absolutify=absolutify, person=person, vouch_form=vouch_form,
                services=services)
    return jingo.render(request, 'phonebook/profile.html', data)


@never_cache
@login_required
def edit_profile(request, unique_id):
    """
    View for editing a profile, typically the user's own.

    Why does this and edit_new_profile accept a unique_id
    Instead of just using the request.user object?

    LDAP's ACL owns if the current user can edit the user or not.
    We get a rich admin screen for free, for LDAPAdmin users.
    """
    return _edit_profile(request, unique_id, False)


@never_cache
@login_required
def edit_new_profile(request, unique_id):
    return _edit_profile(request, unique_id, True)


def _edit_profile(request, unique_id, new_account):
    ldap = UserSession.connect(request)
    try:
        person = ldap.get_by_unique_id(unique_id, use_master=True)
    except NO_SUCH_PERSON:
        log.info('profile_uid Sending 404 for [%s]' % unique_id)
        raise Http404

    del_form = forms.DeleteForm(initial=dict(unique_id=unique_id))

    if person:
        if request.user.unique_id != person.unique_id:
            return HttpResponseForbidden()
        if request.method == 'POST':
            form = forms.ProfileForm(request.POST, request.FILES)
            if form.is_valid():
                ldap.update_person(unique_id, form.cleaned_data)
                ldap.update_profile_photo(unique_id, form.cleaned_data)
                if new_account:
                    return redirect(reverse('confirm_register'))
                else:
                    return redirect(reverse('profile', args=[unique_id]))
        else:
            initial = dict(first_name=person.first_name,
                           last_name=person.last_name,
                           biography=person.biography,)

            initial.update(_get_services_fields(ldap, unique_id,
                                                use_master=True))
            form = forms.ProfileForm(initial=initial)

        return jingo.render(request, 'phonebook/edit_profile.html', dict(
                form=form,
                delete_form=del_form,
                person=person,
                registration_flow=new_account,
                ))
    else:
        raise Http404


def _get_services_fields(ldap, unique_id, use_master=False):
    services = ldap.profile_service_ids(unique_id, use_master)
    irc_nick = None
    irc_nick_unique_id = None

    if MOZILLA_IRC_SERVICE_URI in services:
        irc = services[MOZILLA_IRC_SERVICE_URI]
        irc_nick = irc.service_id
        irc_nick_unique_id = irc.unique_id
    return dict(irc_nickname=irc_nick,
                irc_nickname_unique_id=irc_nick_unique_id,)


class UNAUTHORIZED_DELETE(Exception):
    pass


@never_cache
@login_required
def confirm_delete(request):
    """Display a confirmation page asking the user if they want to leave."""
    del_form = forms.DeleteForm(initial=dict(unique_id=request.user.unique_id))
    return render(request, 'phonebook/confirm_delete.html', {'form': del_form})


@never_cache
@login_required
@require_POST
def delete(request):
    form = forms.DeleteForm(request.POST)
    if form.is_valid() and _user_owns_account(request, form):
        admin_ldap = AdminSession.connect(request)
        admin_ldap.delete_person(form.cleaned_data['unique_id'])
        django.contrib.auth.logout(request)
    else:
        msg = "Unauthorized deletion of account, attempted"
        raise UNAUTHORIZED_DELETE(msg)

    return redirect(reverse('home'))


def _user_owns_account(request, form):
    """
    A leak in our authentication abstraction...
    We use a shared Admin account for deleting, so
    we can't rely on LDAP ACL to test this for us.
    We must ensure the current user is the same as the
    account to be deleted.
    """
    uniq_id_to_delete = form.cleaned_data['unique_id']
    return request.user.unique_id == uniq_id_to_delete


@vouch_required
def search(request):
    people = []
    size_exceeded = False
    form = forms.SearchForm(request.GET)
    if form.is_valid():
        query = form.cleaned_data.get('q', '')
        if request.user.is_authenticated():
            ldap = UserSession.connect(request)
            try:
                # Stale data okay
                people = ldap.search(query)
            except SIZELIMIT_EXCEEDED:
                size_exceeded = True

    return jingo.render(request, 'phonebook/search.html',
                        dict(people=people,
                             form=form,
                             size_exceeded_error=size_exceeded))


@login_required
def photo(request, unique_id):
    needs_master = (request.user.unique_id == unique_id)

    ldap = UserSession.connect(request)
    image = ldap.profile_photo(unique_id, use_master=needs_master)
    if image:
        return HttpResponse(image, mimetype="image/jpeg")
    else:
        return redirect('/media/img/unknown.png')


@login_required
def invited(request, id):
    invite = Invite.objects.get(pk=id)
    return render(request, 'phonebook/invited.html', dict(invite=invite))


@vouch_required
def invite(request):
    if request.method == 'POST':
        f = forms.InviteForm(request.POST)
        if f.is_valid():
            invite = f.save(commit=False)
            invite.inviter = request.user.unique_id
            invite.save()
            subject = _('Become a Mozillian')
            message = _("Hi, I'm sending you this because I think you should "
                        'join mozillians.org, the community directory for '
                        'Mozilla contributors like you. You can create a '
                        'profile for yourself about what you do in the '
                        'community as well as search for other contributors '
                        'to learn more about them or get in touch.  Check it '
                        'out.')
            # l10n: %s is the registration link.
            link = _("Join Mozillians: %s") % invite.get_url()
            message = "%s\n\n%s" % (message, link)
            send_mail(subject, message, request.user.username,
                      [invite.recipient])

            return HttpResponseRedirect(reverse(invited, args=[invite.id]))
    else:
        f = forms.InviteForm()
    data = dict(form=f, foo='bar')

    return jingo.render(request, 'phonebook/invite.html', data)


@vouch_required
@require_POST
def vouch(request):
    form = forms.VouchForm(request.POST)
    if form.is_valid():
        ldap = UserSession.connect(request)
        data = form.cleaned_data
        vouchee = data.get('vouchee')
        ldap.record_vouch(data.get('voucher'), vouchee)
        return redirect(reverse('profile', args=[vouchee]))
