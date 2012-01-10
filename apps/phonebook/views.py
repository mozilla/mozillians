from functools import wraps
from ldap import SIZELIMIT_EXCEEDED
from operator import attrgetter

import django.contrib.auth
from django.contrib import messages
from django.core.cache import cache
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import (Http404, HttpResponse, HttpResponseRedirect,
                         HttpResponseForbidden)
from django.shortcuts import redirect, render
from django.views.decorators.cache import cache_page, never_cache
from django.views.decorators.http import require_POST

import commonware.log
from funfactory.urlresolvers import reverse
from tower import ugettext as _

from browserid.decorators import login_required
from groups.models import Group
from groups.helpers import stringify_groups, users_from_groups
from larper import UserSession, AdminSession, NO_SUCH_PERSON
from larper import MOZILLA_IRC_SERVICE_URI
from phonebook import forms
from phonebook.models import Invite
from session_csrf import anonymous_csrf
from users.models import Anonymous, UserProfile

log = commonware.log.getLogger('m.phonebook')

BAD_VOUCHER = 'Unknown Voucher'


def vouch_required(f):
    """If a user is not vouched they get a 403."""
    @login_required
    @wraps(f)
    def wrapped(request, *args, **kwargs):
        if request.user.get_profile().is_vouched:
            return f(request, *args, **kwargs)
        else:
            log.warning('vouch_required forbidding access')
            return HttpResponseForbidden(_('You must be vouched to do this.'))

    return wrapped


@never_cache
@login_required
def profile_uid(request, unique_id):
    """View a profile by unique_id, which is a stable, random user id."""
    needs_master = (request.user.unique_id == unique_id)
    ldap = UserSession.connect(request)
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
    profile = person.get_profile()

    # TODO: rely more on db for this test
    if not profile.is_vouched and request.user.unique_id != person.unique_id:
        vouch_form = forms.VouchForm(initial=dict(vouchee=person.unique_id))

    services = ldap.profile_service_ids(person.unique_id, use_master)

    person.irc_nickname = None
    if MOZILLA_IRC_SERVICE_URI in services:
        person.irc_nickname = services[MOZILLA_IRC_SERVICE_URI]
        del services[MOZILLA_IRC_SERVICE_URI]

    # Get user groups from their profile.
    groups = person.get_profile().groups.all()

    data = dict(person=person, profile=profile, vouch_form=vouch_form,
                services=services, groups=groups)
    return render(request, 'phonebook/profile.html', data)


@never_cache
@login_required
def edit_profile(request):
    """View for editing the current user's profile."""
    return _edit_profile(request, False)


@never_cache
@anonymous_csrf
def edit_new_profile(request):
    return _edit_profile(request, True)


def _edit_profile(request, new_account):
    ldap = UserSession.connect(request)
    unique_id = request.user.unique_id
    try:
        person = ldap.get_by_unique_id(unique_id, use_master=True)
    except NO_SUCH_PERSON:
        log.info('profile_uid Sending 404 for [%s]' % unique_id)
        raise Http404

    del_form = forms.DeleteForm(initial=dict(unique_id=unique_id))

    if not person:
        raise Http404

    if request.user.unique_id != person.unique_id:
        return HttpResponseForbidden()

    profile = request.user.get_profile()
    user_groups = stringify_groups(profile.groups.all().order_by('name'))

    if request.method == 'POST':
        form = forms.ProfileForm(request.POST, request.FILES)
        if form.is_valid():
            # Save both LDAP and RDBS data via our ProfileForm
            ldap.update_person(unique_id, form.cleaned_data)
            ldap.update_profile_photo(unique_id, form.cleaned_data)

            form.save(request, ldap)

            return redirect(reverse('confirm_register') if new_account
                            else reverse('profile', args=[unique_id]))
    else:
        initial = dict(first_name=person.first_name,
                       last_name=person.last_name,
                       biography=person.biography,
                       website=profile.website,
                       groups=user_groups)

        initial.update(_get_services_fields(ldap, unique_id,
                                            use_master=True))
        form = forms.ProfileForm(initial=initial)

    d = dict(form=form,
             edit_form_action=reverse('phonebook.edit_profile'),
             delete_form=del_form,
             person=person,
             email=person.username,
             registration_flow=new_account,
             user_groups=user_groups,
             photo=ldap.profile_photo(unique_id, use_master=True),
            )
    return render(request, 'phonebook/edit_profile.html', d)


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
    limit = None
    nonvouched_only = False
    people = []
    size_exceeded = False
    show_pagination = False
    form = forms.SearchForm(request.GET)

    if form.is_valid():
        query = form.cleaned_data.get('q', '')
        limit = form.cleaned_data['limit']
        nonvouched_only = form.cleaned_data['nonvouched_only']

        if request.user.is_authenticated():
            ldap = UserSession.connect(request)
            try:
                # Stale data okay
                sortk = attrgetter('full_name')
                people = sorted(ldap.search(query,
                                            nonvouched_only=nonvouched_only),
                                            key=sortk)

                # Search based on group name as well
                groups = Group.objects.filter(name__icontains=query)[:limit]
                for group in groups:
                    for user in users_from_groups(request, group,
                            limit=forms.PAGINATION_LIMIT,
                            nonvouched_only=nonvouched_only):
                        if not user.unique_id in [p.unique_id for p in people]:
                            people.append(user)

                paginator = Paginator(people, limit)
                page = request.GET.get('page', 1)
                try:
                    people = paginator.page(page)
                except PageNotAnInteger:
                    people = paginator.page(1)
                except EmptyPage:
                    people = paginator.page(paginator.num_pages)

                if paginator.count > forms.PAGINATION_LIMIT:
                    show_pagination = True

            except SIZELIMIT_EXCEEDED:
                size_exceeded = True

<<<<<<< HEAD
            if len(people) == 1 and not show_pagination:
                return redirect(reverse('profile', args=[people[0].unique_id]))
=======
            if len(people) == 1:
                return profile_uid(request, people[0].unique_id)
>>>>>>> e3d7645... Fixes bug 694660 - if there is only one search result show that

    d = dict(people=people,
             form=form,
             limit=limit,
             nonvouched_only=nonvouched_only,
             show_pagination=show_pagination,
             size_exceeded_error=size_exceeded)
    return render(request, 'phonebook/search.html', d)


@cache_page(60 * 60 * 168)  # 1 week.
def search_plugin(request):
    """Render an OpenSearch Plugin."""
    return render(request, 'phonebook/search_opensearch.xml',
                  content_type='application/opensearchdescription+xml')


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
            ldap = UserSession.connect(request)
            unique_id = request.user.unique_id
            try:
                person = ldap.get_by_unique_id(unique_id, use_master=True)
            except NO_SUCH_PERSON:
                log.info('profile_uid Sending 404 for [%s]' % unique_id)
                raise Http404

            invite = f.save(commit=False)
            invite.inviter = request.user.unique_id
            invite.save()
            invite.send(sender=person)

            return HttpResponseRedirect(reverse(invited, args=[invite.id]))
    else:
        f = forms.InviteForm()
    data = dict(form=f, foo='bar')

    return render(request, 'phonebook/invite.html', data)


@vouch_required
@require_POST
def vouch(request):
    """
    When a voucher approves a vouch for a vouchee, there
    can be a replication lag between master -> slave. As a
    result, there is a possibility that viewing the vouchee's
    profile will not show the updated state. So we currently
    will cache the state for immediate feedback.
    """
    form = forms.VouchForm(request.POST)
    if form.is_valid():
        data = form.cleaned_data
        vouchee = data.get('vouchee')
        # TODO: make the form give us the User's id...
        p = UserProfile.objects.get_by_unique_id(vouchee)
        p.vouch(request.user.get_profile())

        # TODO: Is this still necessary?...
        cache.set('vouched_' + vouchee, True)

        # Notify the current user that they vouched successfully.
        msg = _(u'Thanks for vouching for a fellow Mozillian! '
                 'This user is now vouched!')
        messages.info(request, msg)

        return redirect(reverse('profile', args=[vouchee]))
