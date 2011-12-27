from functools import wraps

import django.contrib.auth
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import (Http404, HttpResponse, HttpResponseRedirect,
                         HttpResponseForbidden)
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_page, never_cache
from django.views.decorators.http import require_POST

import commonware.log
from funfactory.urlresolvers import reverse
from tower import ugettext as _

from groups.helpers import stringify_groups
from larper import UserSession, AdminSession, NO_SUCH_PERSON
from larper import MOZILLA_IRC_SERVICE_URI
from phonebook import forms
from phonebook.models import Invite
from users.models import UserProfile

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
def profile(request, username):
    """View a profile by username."""
    user = get_object_or_404(User, username=username)

    vouch_form = None
    profile = user.get_profile()

    if not profile.is_vouched and request.user.username != username:
        voucher = request.user.username
        vouch_form = forms.VouchForm(initial=dict(vouchee=profile.pk))

    # Get user groups from their profile.
    groups = profile.groups.all()

    data = dict(user=user, profile=profile, vouch_form=vouch_form,
                groups=groups)
    return render(request, 'phonebook/profile.html', data)


# TODO: consolidatify
@never_cache
@login_required
def edit_new_profile(request):
    return edit_profile(request, True)


@never_cache
@login_required
def edit_profile(request, new_account=False):
    profile = request.user.get_profile()
    user_groups = stringify_groups(profile.groups.all().order_by('name'))

    if request.method == 'POST':

        form = forms.ProfileForm(request.POST, request.FILES)
        if form.is_valid():
            form.save(request)
            next = (reverse('confirm_register') if new_account
                    else reverse('profile', args=[request.user.username]))
            return redirect(next)
    else:
        initial = dict(first_name=request.user.first_name,
                       last_name=request.user.last_name,
                       biography=profile.bio,
                       website=profile.website,
                       irc_nickname=profile.ircname,
                       groups=user_groups)

        form = forms.ProfileForm(initial=initial)

    d = dict(form=form,
             registration_flow=new_account,
             user_groups=user_groups)
    return render(request, 'phonebook/edit_profile.html', d)


@never_cache
@login_required
def confirm_delete(request):
    """Display a confirmation page asking the user if they want to leave."""
    return render(request, 'phonebook/confirm_delete.html')


@never_cache
@login_required
@require_POST
def delete(request):
    delete_me = request.user.pk
    logout(request)
    User.objects.get(pk=delete_me).delete()
    log.info('Deleting %d' % delete_me)
    return redirect(reverse('home'))


@vouch_required
def search(request):
    limit = None
    nonvouched_only = False
    people = []
    show_pagination = False
    form = forms.SearchForm(request.GET)

    if form.is_valid():
        query = form.cleaned_data.get('q', '')
        limit = form.cleaned_data['limit']
        vouched = False if form.cleaned_data['nonvouched_only'] else None

        if request.user.is_authenticated():
            profiles = UserProfile.search(query, vouched=vouched)

            paginator = Paginator(profiles, limit)
            page = request.GET.get('page', 1)

            try:
                people = paginator.page(page)
            except PageNotAnInteger:
                people = paginator.page(1)
            except EmptyPage:
                people = paginator.page(paginator.num_pages)

            if paginator.count > forms.PAGINATION_LIMIT:
                show_pagination = True

    d = dict(people=people,
             form=form,
             limit=limit,
             nonvouched_only=nonvouched_only,
             show_pagination=show_pagination)
    return render(request, 'phonebook/search.html', d)


@cache_page(60 * 60 * 168)  # 1 week.
def search_plugin(request):
    """Render an OpenSearch Plugin."""
    return render(request, 'phonebook/search_opensearch.xml',
                  content_type='application/opensearchdescription+xml')


@login_required
def invited(request, id):
    invite = Invite.objects.get(pk=id)
    return render(request, 'phonebook/invited.html', dict(invite=invite))


@vouch_required
def invite(request):
    if request.method == 'POST':
        f = forms.InviteForm(request.POST)
        if f.is_valid():
            profile = request.user.get_profile()
            invite = f.save(profile)
            invite.send(sender=profile)
            return HttpResponseRedirect(reverse(invited, args=[invite.id]))
    else:
        f = forms.InviteForm()
    data = dict(form=f, foo='bar')

    return render(request, 'phonebook/invite.html', data)


@vouch_required
@require_POST
def vouch(request):
    """Vouch a user."""
    form = forms.VouchForm(request.POST)

    if form.is_valid():
        p = UserProfile.objects.get(pk=form.cleaned_data.get('vouchee'))
        p.vouch(request.user.get_profile())

        # Notify the current user that they vouched successfully.
        msg = _(u'Thanks for vouching for a fellow Mozillian! '
                 'This user is now vouched!')
        messages.info(request, msg)

        return redirect(reverse('profile', args=[p.user.username]))

    return HttpResponseForbidden
