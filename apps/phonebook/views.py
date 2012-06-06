from functools import wraps

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.cache import cache_page, never_cache
from django.views.decorators.http import require_POST

import commonware.log
from funfactory.urlresolvers import reverse
from tastypie.models import ApiKey
from tower import ugettext as _

from groups.helpers import stringify_groups
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

    if not profile.is_vouched and request.user.get_profile().is_vouched:
        vouch_form = forms.VouchForm(initial=dict(vouchee=profile.pk))

    data = dict(shown_user=user, profile=profile, vouch_form=vouch_form)
    return render(request, 'phonebook/profile.html', data)


@never_cache
@login_required
def edit_profile(request):
    profile = request.user.get_profile()
    user_groups = stringify_groups(profile.groups.all().order_by('name'))
    user_skills = stringify_groups(profile.skills.all().order_by('name'))

    if request.method == 'POST':
        form = forms.ProfileForm(
                request.POST,
                request.FILES,
                instance=profile,
        )
        if form.is_valid():
            old_username = request.user.username
            form.save(request)
            if 'reset_api_key' in request.POST:
                try:
                    request.user.api_key.delete()
                except ApiKey.DoesNotExist:
                    pass
                return redirect(reverse('profile.edit'))

            # Notify the user that their old profile URL won't work.
            if (not profile.is_vouched and
                request.user.username != old_username):
                messages.info(request, _(u'You changed your username; please '
                                          'note your profile URL has also '
                                          'changed.'))

            return redirect(reverse('profile', args=[request.user.username]))

    initial = dict(first_name=request.user.first_name,
                   last_name=request.user.last_name,
                   bio=profile.bio,
                   website=profile.website,
                   irc_nickname=profile.ircname,
                   groups=user_groups,
                   skills=user_skills)

    if not request.user.username.startswith('u/'):
        initial.update(username=request.user.username)

    form = forms.ProfileForm(
            instance=profile,
            initial=initial,
    )

    # When changing this keep in mind that the same view is used for
    # user.register.
    d = dict(form=form,
             mode='edit',
             user_groups=user_groups,
             my_vouches=UserProfile.objects.filter(vouched_by=profile),
             profile=profile)
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
    removed = User.objects.get(pk=delete_me)
    removed.get_profile().anonymize()
    log.info('Deleting %d' % removed.id)
    return redirect(reverse('home'))


@vouch_required
def search(request):
    num_pages = 0
    limit = None
    nonvouched_only = False
    picture_only = False
    people = []
    show_pagination = False
    form = forms.SearchForm(request.GET)

    if form.is_valid():
        query = form.cleaned_data.get('q', u'')
        limit = form.cleaned_data['limit']
        vouched = False if form.cleaned_data['nonvouched_only'] else None
        profilepic = True if form.cleaned_data['picture_only'] else None
        page = request.GET.get('page', 1)

        # If nothing has been entered don't load any searches.
        if not (not query and vouched is None and profilepic is None):
            profiles = UserProfile.search(query,
                                          vouched=vouched,
                                          photo=profilepic)

            paginator = Paginator(profiles, limit)

            try:
                people = paginator.page(page)
            except PageNotAnInteger:
                people = paginator.page(1)
            except EmptyPage:
                people = paginator.page(paginator.num_pages)

            if len(profiles) == 1:
                return redirect(reverse('profile',
                                        args=[people[0].user.username]))

            if paginator.count > forms.PAGINATION_LIMIT:
                show_pagination = True
                num_pages = len(people.paginator.page_range)

    d = dict(people=people,
             form=form,
             limit=limit,
             nonvouched_only=nonvouched_only,
             picture_only=picture_only,
             show_pagination=show_pagination,
             num_pages=num_pages)

    if request.is_ajax():
        return render(request, 'search_ajax.html', d)

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
    data = dict(form=f)

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
