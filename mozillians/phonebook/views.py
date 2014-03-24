from django.conf import settings
from django.contrib import auth
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.cache import cache_page, never_cache
from django.views.decorators.http import require_POST

from django_browserid.base import get_audience, verify
from django_browserid.views import Verify
from funfactory.helpers import urlparams
from funfactory.urlresolvers import reverse
from tower import ugettext as _

import mozillians.phonebook.forms as forms
from mozillians.common.decorators import allow_public, allow_unvouched
from mozillians.common.helpers import redirect
from mozillians.common.middleware import LOGIN_MESSAGE, GET_VOUCHED_MESSAGE
from mozillians.groups.helpers import stringify_groups
from mozillians.groups.models import Group
from mozillians.phonebook.models import Invite
from mozillians.phonebook.utils import update_invites
from mozillians.users.managers import EMPLOYEES, MOZILLIANS, PUBLIC, PRIVILEGED
from mozillians.users.models import COUNTRIES, UserProfile


class BrowserIDVerify(Verify):
    def form_valid(self, form):
        """Custom form validation to support email changing.

        If user is already authenticated and reaches this point, it's
        an email changing procedure. Validate that email is good and
        save it in the database.

        Otherwise continue with the default django-browserid verification.
        """
        if not self.request.user.is_authenticated():
            return super(BrowserIDVerify, self).form_valid(form)

        failure_url = urlparams(reverse('phonebook:profile_edit'), bid_login_failed=1)
        self.assertion = form.cleaned_data['assertion']
        self.audience = get_audience(self.request)
        result = verify(self.assertion, self.audience)
        if not result:
            messages.error(self.request, _('Authentication failed.'))
            return redirect(failure_url)

        email = result['email']

        if User.objects.filter(email=email).exists():
            messages.error(self.request, _('Email already exists in the database.'))
            return redirect('phonebook:logout')

        user = self.request.user
        user.email = email
        user.save()
        return redirect('phonebook:profile_view', user.username)


@allow_unvouched
def login(request):
    if request.user.userprofile.is_complete:
        return redirect('phonebook:home')
    return redirect('phonebook:profile_edit')


@never_cache
@allow_public
def home(request):
    return render(request, 'phonebook/home.html')


@allow_public
@never_cache
def view_profile(request, username):
    """View a profile by username."""
    data = {}
    privacy_mappings = {'anonymous': PUBLIC, 'mozillian': MOZILLIANS, 'employee': EMPLOYEES,
                        'privileged': PRIVILEGED, 'myself': None}
    privacy_level = None

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

        if (not profile.is_vouched
            and request.user.is_authenticated()
            and request.user.userprofile.is_vouched):
                data['vouch_form'] = (
                    forms.VouchForm(initial={'vouchee': profile.pk}))

    data['shown_user'] = profile.user
    data['profile'] = profile
    data['groups'] = profile.get_annotated_groups()
    data['locale'] = request.locale

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
                        instance=profile, locale=request.locale,
                        initial=dict(skills=user_skills))

    email_form = forms.EmailForm(request.POST or None,
                                 initial={'email': request.user.email,
                                          'user_id': request.user.id})

    if (user_form.is_valid() and profile_form.is_valid() and
        accounts_formset.is_valid() and email_form.is_valid() and
            language_formset.is_valid()):
        old_username = request.user.username
        user_form.save()
        profile_form.save()
        accounts_formset.save()
        language_formset.save()

        # Notify the user that their old profile URL won't work.
        if new_profile:
            update_invites(request)
            messages.info(request, _(u'Your account has been created.'))
        elif user.username != old_username:
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
                my_vouches=UserProfile.objects.filter(vouched_by=profile),
                profile=request.user.userprofile,
                apps=user.apiapp_set.filter(is_active=True),
                language_formset=language_formset)

    # If there are form errors, don't send a 200 OK.
    status = 400 if (profile_form.errors or user_form.errors) else 200
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
    messages.info(request, _('Your account has been deleted. '
                             'Thanks for being a Mozillian!'))
    # We don't redirect to logout view, because delete already logs
    # out user. Instead we render the logout template to BrowserID
    # logout.
    return render(request, 'phonebook/logout.html')


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

    if request.is_ajax():
        return render(request, 'search_ajax.html', d)

    return render(request, 'phonebook/search.html', d)


@allow_public
@cache_page(60 * 60 * 168)  # 1 week.
def search_plugin(request):
    """Render an OpenSearch Plugin."""
    return render(request, 'phonebook/search_opensearch.xml',
                  content_type='application/opensearchdescription+xml')


def invite(request):
    profile = request.user.userprofile
    invite_form = forms.InviteForm(request.POST or None,
                                   instance=Invite(inviter=profile))
    if request.method == 'POST' and invite_form.is_valid():
        invite = invite_form.save()
        invite.send(sender=profile)
        msg = _(u"%s has been invited to Mozillians. They'll receive an email "
                u"with instructions on how to join. You can "
                u"invite another Mozillian if you like." % invite.recipient)
        messages.success(request, msg)
        return redirect('phonebook:home')

    return render(request, 'phonebook/invite.html',
                  {'invite_form': invite_form})


@require_POST
def vouch(request):
    """Vouch a user."""
    form = forms.VouchForm(request.POST)

    if form.is_valid():
        p = UserProfile.objects.get(pk=form.cleaned_data.get('vouchee'))
        p.vouch(request.user.userprofile)

        # Notify the current user that they vouched successfully.
        msg = _(u'Thanks for vouching for a fellow Mozillian! '
                u'This user is now vouched!')
        messages.info(request, msg)
        return redirect('phonebook:profile_view', p.user.username)

    return HttpResponseBadRequest()


def list_mozillians_in_location(request, country, region=None, city=None):
    country = country.lower()
    country_name = COUNTRIES.get(country, country)
    queryset = UserProfile.objects.vouched().filter(country=country)
    show_pagination = False

    if city:
        queryset = queryset.filter(city__iexact=city)
    if region:
        queryset = queryset.filter(region__iexact=region)

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
            'country_name': country_name,
            'city_name': city,
            'region_name': region,
            'page': page,
            'show_pagination': show_pagination}
    return render(request, 'phonebook/location-list.html', data)


@allow_unvouched
def logout(request):
    """Logout view that wraps Django's logout but always redirects.

    Django's contrib.auth.views logout method renders a template if
    the `next_page` argument is `None`, which we don't want. This view
    always returns an HTTP redirect instead.

    """
    return auth.views.logout(request, template_name='phonebook/logout.html')


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
                update_invites(request)
        else:
            messages.info(request, _("You've been invited to join Mozillians.org! "
                                     "Sign in and then you can create a profile."))

    return redirect('phonebook:home')
