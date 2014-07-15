from django.conf import settings
from django.contrib.auth.views import logout as auth_logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.cache import cache_page, never_cache
from django.views.decorators.http import require_POST

from funfactory.urlresolvers import reverse
from tower import ugettext as _
from waffle.decorators import waffle_flag

import mozillians.phonebook.forms as forms
from mozillians.common.decorators import allow_public, allow_unvouched
from mozillians.common.helpers import redirect
from mozillians.common.middleware import LOGIN_MESSAGE, GET_VOUCHED_MESSAGE
from mozillians.groups.helpers import stringify_groups
from mozillians.groups.models import Group
from mozillians.phonebook.models import Invite
from mozillians.phonebook.utils import redeem_invite
from mozillians.users.managers import EMPLOYEES, MOZILLIANS, PUBLIC, PRIVILEGED
from mozillians.users.models import UserProfile


@allow_unvouched
def login(request):
    if request.user.userprofile.is_complete:
        return redirect('phonebook:home')
    return redirect('phonebook:profile_edit')


@never_cache
@allow_public
def home(request):
    return render(request, 'phonebook/home.html')


@waffle_flag('testing-autovouch-views')
@allow_unvouched
@never_cache
def vouch(request, username):
    """Automatically vouch username.

    This must be behind a waffle flag and activated only for testing
    purposes.

    """
    profile = get_object_or_404(UserProfile, user__username=username)
    now = timezone.now()
    description = 'Automatically vouched for testing purposes on {0}'.format(now)
    profile.vouch(None, description=description, autovouch=True)
    messages.success(request, _('Successfully vouched user.'))
    return redirect('phonebook:profile_view', profile.user.username)


@waffle_flag('testing-autovouch-views')
@allow_unvouched
@never_cache
def unvouch(request, username):
    """Automatically remove all vouches from username.

    This must be behind a waffle flag and activated only for testing
    purposes.

    """
    profile = get_object_or_404(UserProfile, user__username=username)
    profile.vouches_received.all().delete()
    messages.success(request, _('Successfully unvouched user.'))
    return redirect('phonebook:profile_view', profile.user.username)


@allow_public
@never_cache
def view_profile(request, username):
    """View a profile by username."""
    data = {}
    privacy_mappings = {'anonymous': PUBLIC, 'mozillian': MOZILLIANS, 'employee': EMPLOYEES,
                        'privileged': PRIVILEGED, 'myself': None}
    privacy_level = None
    profile_is_vouchable = False

    if (request.user.is_authenticated() and request.user.username == username):
        # own profile
        view_as = request.GET.get('view_as', 'myself')
        privacy_level = privacy_mappings.get(view_as, None)
        profile = UserProfile.objects.privacy_level(privacy_level).get(user__username=username)
        data['privacy_mode'] = view_as
    else:
        userprofile_query = UserProfile.objects.filter(user__username=username)
        public_profile_exists = userprofile_query.public().exists()
        profile_exists = userprofile_query.exists()
        profile_complete = userprofile_query.exclude(full_name='').exists()

        if not public_profile_exists:
            if not request.user.is_authenticated():
                # you have to be authenticated to continue
                messages.warning(request, LOGIN_MESSAGE)
                return (login_required(view_profile, login_url=reverse('phonebook:home'))
                        (request, username))

            if not request.user.userprofile.is_vouched:
                # you have to be vouched to continue
                messages.error(request, GET_VOUCHED_MESSAGE)
                return redirect('phonebook:home')

        if not profile_exists or not profile_complete:
            raise Http404

        profile = UserProfile.objects.get(user__username=username)
        profile.set_instance_privacy_level(PUBLIC)
        if request.user.is_authenticated():
            profile.set_instance_privacy_level(
                request.user.userprofile.privacy_level)

        if (request.user.is_authenticated() and profile.is_vouchable(request.user.userprofile)):
            profile_is_vouchable = True

            vouch_form = forms.VouchForm(request.POST or None)
            data['vouch_form'] = vouch_form
            if vouch_form.is_valid():
                # We need to re-fetch profile from database.
                profile = UserProfile.objects.get(user__username=username)
                profile.vouch(request.user.userprofile, vouch_form.cleaned_data['description'])
                # Notify the current user that they vouched successfully.
                msg = _(u'Thanks for vouching for a fellow Mozillian! This user is now vouched!')
                messages.info(request, msg)
                return redirect('phonebook:profile_view', profile.user.username)

    data['profile_is_vouchable'] = profile_is_vouchable
    data['shown_user'] = profile.user
    data['profile'] = profile
    data['groups'] = profile.get_annotated_groups()

    # Only show pending groups if user is looking at their own profile,
    # or current user is a superuser
    if not (request.user.is_authenticated()
            and (request.user.username == username or request.user.is_superuser)):
        data['groups'] = [grp for grp in data['groups'] if not grp.pending]

    return render(request, 'phonebook/profile.html', data)


@allow_unvouched
@never_cache
def edit_profile(request):
    """Edit user profile view."""
    # Don't user request.user
    user = User.objects.get(pk=request.user.id)
    profile = user.userprofile
    user_groups = profile.groups.all().order_by('name')
    user_skills = stringify_groups(profile.skills.all().order_by('name'))

    user_form = forms.UserForm(request.POST or None, instance=user)
    accounts_formset = forms.AccountsFormset(request.POST or None, instance=profile)
    new_profile = False
    form = forms.ProfileForm
    language_formset = forms.LanguagesFormset(request.POST or None,
                                              instance=profile,
                                              locale=request.locale)

    if not profile.is_complete:
        new_profile = True
        form = forms.RegisterForm

    profile_form = form(request.POST or None, request.FILES or None,
                        instance=profile,
                        initial={'skills': user_skills,
                                 'saveregion': True if profile.geo_region else False,
                                 'savecity': True if profile.geo_city else False,
                                 'lat': profile.lat,
                                 'lng': profile.lng})

    email_form = forms.EmailForm(request.POST or None,
                                 initial={'email': request.user.email,
                                          'user_id': request.user.id})

    all_forms = [user_form, profile_form, accounts_formset, email_form,
                 language_formset]

    # Using ``list`` to force calling is_valid on all the forms, even if earlier
    # ones are not valid, so we detect and display all the errors.
    if all(list(f.is_valid() for f in all_forms)):
        old_username = request.user.username
        user_form.save()
        profile_form.save()
        accounts_formset.save()
        language_formset.save()

        if new_profile:
            redeem_invite(profile, request.session.get('invite-code'))
            messages.info(request, _(u'Your account has been created.'))
        elif user.username != old_username:
            # Notify the user that their old profile URL won't work.
            messages.info(request,
                          _(u'You changed your username; please note your '
                            u'profile URL has also changed.'))

        if email_form.email_changed():
            return render(request, 'phonebook/verify_email.html',
                          {'email': email_form.cleaned_data['email']})
        return redirect('phonebook:profile_view', user.username)

    data = dict(profile_form=profile_form,
                user_form=user_form,
                accounts_formset=accounts_formset,
                email_form=email_form,
                user_groups=user_groups,
                profile=request.user.userprofile,
                apps=user.apiapp_set.filter(is_active=True),
                language_formset=language_formset,
                mapbox_id=settings.MAPBOX_PROFILE_ID)

    # If there are form errors, don't send a 200 OK.
    status = 400 if any(f.errors for f in all_forms) else 200
    return render(request, 'phonebook/edit_profile.html', data, status=status)


@allow_unvouched
@never_cache
def confirm_delete(request):
    """Display a confirmation page asking the user if they want to
    leave.

    """
    return render(request, 'phonebook/confirm_delete.html')


@allow_unvouched
@never_cache
@require_POST
def delete(request):
    request.user.delete()
    messages.info(request, _('Your account has been deleted. Thanks for being a Mozillian!'))
    return logout(request)


@allow_public
def search(request):
    limit = None
    people = []
    show_pagination = False
    form = forms.SearchForm(request.GET)
    groups = None
    functional_areas = None

    if form.is_valid():
        query = form.cleaned_data.get('q', u'')
        limit = form.cleaned_data['limit']
        include_non_vouched = form.cleaned_data['include_non_vouched']
        page = request.GET.get('page', 1)
        functional_areas = Group.get_functional_areas()
        public = not (request.user.is_authenticated()
                      and request.user.userprofile.is_vouched)

        profiles = UserProfile.search(query, public=public,
                                      include_non_vouched=include_non_vouched)
        if not public:
            groups = Group.search(query)

        paginator = Paginator(profiles, limit)

        try:
            people = paginator.page(page)
        except PageNotAnInteger:
            people = paginator.page(1)
        except EmptyPage:
            people = paginator.page(paginator.num_pages)

        if profiles.count() == 1 and not groups:
            return redirect('phonebook:profile_view', people[0].user.username)

        show_pagination = paginator.count > settings.ITEMS_PER_PAGE

    d = dict(people=people,
             search_form=form,
             limit=limit,
             show_pagination=show_pagination,
             groups=groups,
             functional_areas=functional_areas)

    return render(request, 'phonebook/search.html', d)


@waffle_flag('betasearch')
@allow_public
def betasearch(request):
    """This view is for researching new search and data filtering
    options. It will eventually replace the 'search' view.

    This view is behind the 'betasearch' waffle flag.
    """
    limit = None
    people = []
    show_pagination = False
    form = forms.SearchForm(request.GET)
    groups = None
    functional_areas = None

    if form.is_valid():
        query = form.cleaned_data.get('q', u'')
        limit = form.cleaned_data['limit']
        include_non_vouched = form.cleaned_data['include_non_vouched']
        page = request.GET.get('page', 1)
        functional_areas = Group.get_functional_areas()
        public = not (request.user.is_authenticated()
                      and request.user.userprofile.is_vouched)

        profiles = UserProfile.search(query, public=public,
                                      include_non_vouched=include_non_vouched)
        if not public:
            groups = Group.search(query)

        paginator = Paginator(profiles, limit)

        try:
            people = paginator.page(page)
        except PageNotAnInteger:
            people = paginator.page(1)
        except EmptyPage:
            people = paginator.page(paginator.num_pages)

        if profiles.count() == 1 and not groups:
            return redirect('phonebook:profile_view', people[0].user.username)

        show_pagination = paginator.count > settings.ITEMS_PER_PAGE

    d = dict(people=people,
             search_form=form,
             limit=limit,
             show_pagination=show_pagination,
             groups=groups,
             functional_areas=functional_areas)

    return render(request, 'phonebook/betasearch.html', d)


@allow_public
@cache_page(60 * 60 * 168)  # 1 week.
def search_plugin(request):
    """Render an OpenSearch Plugin."""
    return render(request, 'phonebook/search_opensearch.xml',
                  content_type='application/opensearchdescription+xml')


def invite(request):
    profile = request.user.userprofile
    invite_form = None
    vouch_form = None
    if profile.can_vouch:
        invite_form = forms.InviteForm(request.POST or None,
                                       instance=Invite(inviter=profile))
        vouch_form = forms.VouchForm(request.POST or None)

    if invite_form and vouch_form and invite_form.is_valid() and vouch_form.is_valid():
        invite_form.instance.reason = vouch_form.cleaned_data['description']
        invite = invite_form.save()
        invite.send(sender=profile, personal_message=invite_form.cleaned_data['message'])
        msg = _(u"%s has been invited to Mozillians. They'll receive an email "
                u"with instructions on how to join. You can "
                u"invite another Mozillian if you like.") % invite.recipient
        messages.success(request, msg)
        return redirect('phonebook:invite')

    return render(request, 'phonebook/invite.html',
                  {
                      'invite_form': invite_form,
                      'vouch_form': vouch_form,
                      'invites': profile.invites.all(),
                      'vouch_threshold': settings.CAN_VOUCH_THRESHOLD,
                  })


@require_POST
def delete_invite(request, invite_pk):
    profile = request.user.userprofile
    deleted_invite = get_object_or_404(Invite, pk=invite_pk, inviter=profile, redeemed=None)
    deleted_invite.delete()

    msg = (_(u"%s's invitation to Mozillians has been revoked. "
             u"You can invite %s again if you like.") %
            (deleted_invite.recipient, deleted_invite.recipient))
    messages.success(request, msg)
    return redirect('phonebook:invite')


def list_mozillians_in_location(request, country, region=None, city=None):
    queryset = UserProfile.objects.vouched().filter(geo_country__name__iexact=country)
    show_pagination = False

    if city:
        queryset = queryset.filter(geo_city__name__iexact=city)
    if region:
        queryset = queryset.filter(geo_region__name__iexact=region)

    paginator = Paginator(queryset, settings.ITEMS_PER_PAGE)
    page = request.GET.get('page', 1)

    try:
        people = paginator.page(page)
    except PageNotAnInteger:
        people = paginator.page(1)
    except EmptyPage:
        people = paginator.page(paginator.num_pages)

    if paginator.count > settings.ITEMS_PER_PAGE:
        show_pagination = True

    data = {'people': people,
            'country_name': country,
            'city_name': city,
            'region_name': region,
            'page': page,
            'show_pagination': show_pagination}
    return render(request, 'phonebook/location_list.html', data)


@allow_unvouched
def logout(request):
    """View that logs out the user and redirects to home page."""
    auth_logout(request)
    return redirect('phonebook:home')


@allow_public
def register(request):
    """Registers Users.

    Pulls out an invite code if it exists and auto validates the user
    if so. Single-purpose view.
    """
    # TODO already vouched users can be re-vouched?
    if 'code' in request.GET:
        request.session['invite-code'] = request.GET['code']
        if request.user.is_authenticated():
            if not request.user.userprofile.is_vouched:
                redeem_invite(request.user.userprofile, request.session['invite-code'])
        else:
            messages.info(request, _("You've been invited to join Mozillians.org! "
                                     "Sign in and then you can create a profile."))

    return redirect('phonebook:home')
