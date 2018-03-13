import json
import logging
import requests
from urllib import urlencode

from django.conf import settings
from django.contrib.auth.views import logout as auth_logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.encoding import force_bytes, smart_bytes
from django.utils.safestring import mark_safe
from django.views.decorators.cache import cache_control, never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import View

from django.utils.translation import ugettext as _
from haystack.generic_views import SearchView
from haystack.query import EmptySearchQuerySet
from josepy.jwk import JWK
from josepy.jws import JWS
from mozilla_django_oidc.views import OIDCAuthenticationRequestView, get_next_url
from mozilla_django_oidc.utils import absolutify, import_from_settings
from raven.contrib.django.models import client
from waffle import flag_is_active
from waffle.decorators import waffle_flag

import mozillians.phonebook.forms as forms
from mozillians.api.models import APIv2App
from mozillians.common.decorators import allow_public, allow_unvouched
from mozillians.common.middleware import LOGIN_MESSAGE, GET_VOUCHED_MESSAGE
from mozillians.common.templatetags.helpers import (get_object_or_none, nonprefixed_url, redirect,
                                                    urlparams)
from mozillians.common.urlresolvers import reverse
from mozillians.groups.models import Group
from mozillians.phonebook.models import Invite
from mozillians.phonebook.utils import redeem_invite
from mozillians.users.managers import EMPLOYEES, MOZILLIANS, PUBLIC, PRIVATE
from mozillians.users.models import AbuseReport, ExternalAccount, IdpProfile, UserProfile
from mozillians.users.tasks import (check_spam_account, send_userprofile_to_cis,
                                    update_email_in_basket)


@allow_unvouched
def login(request):
    if request.user.userprofile.is_complete:
        return redirect('phonebook:home')
    return redirect('phonebook:profile_edit')


@never_cache
@allow_public
def home(request):
    show_start = False
    if request.GET.get('source', ''):
        show_start = True

    bugzilla_url = 'https://bugzilla.mozilla.org/enter_bug.cgi?product=Participation%20Infrastructure&component=Phonebook'  # noqa
    link = '<a href="{}">file a bug</a>'.format(bugzilla_url)
    msg = 'In case you are facing authentication issues please {}'.format(link)
    messages.warning(request, mark_safe(msg))
    return render(request, 'phonebook/home.html', {'show_start': show_start})


@allow_unvouched
@never_cache
def vouch(request, username):
    """Automatically vouch username.

    This must be behind a waffle flag and activated only for testing
    purposes.

    """
    if flag_is_active(request, 'testing-autovouch-views'):
        profile = get_object_or_404(UserProfile, user__username=username)
        now = timezone.now()
        description = 'Automatically vouched for testing purposes on {0}'.format(now)
        vouch = profile.vouch(None, description=description, autovouch=True)
        if vouch:
            messages.success(request, _('Successfully vouched user.'))
        else:
            msg = _('User not vouched. Maybe there are {0} vouches already?')
            msg = msg.format(settings.VOUCH_COUNT_LIMIT)
            messages.error(request, msg)

        return redirect('phonebook:profile_view', profile.user.username)
    raise Http404


@allow_unvouched
@never_cache
def unvouch(request, username):
    """Automatically remove all vouches from username.

    This must be behind a waffle flag and activated only for testing
    purposes.

    """
    if flag_is_active(request, 'testing-autovouch-views'):
        profile = get_object_or_404(UserProfile, user__username=username)
        profile.vouches_received.all().delete()
        messages.success(request, _('Successfully unvouched user.'))
        return redirect('phonebook:profile_view', profile.user.username)
    raise Http404


@allow_public
@never_cache
def view_profile(request, username):
    """View a profile by username."""
    data = {}
    privacy_mappings = {'anonymous': PUBLIC, 'mozillian': MOZILLIANS, 'employee': EMPLOYEES,
                        'private': PRIVATE, 'myself': None}
    privacy_level = None
    abuse_form = None

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

        if (request.user.is_authenticated() and request.user.userprofile.is_vouched and
                not profile.can_vouch):
            abuse_report = get_object_or_none(AbuseReport, reporter=request.user.userprofile,
                                              profile=profile)

            if not abuse_report:
                abuse_report = AbuseReport(reporter=request.user.userprofile, profile=profile)

            abuse_form = forms.AbuseReportForm(request.POST or None, instance=abuse_report)
            if abuse_form.is_valid():
                abuse_form.save()
                msg = _(u'Thanks for helping us improve mozillians.org!')
                messages.info(request, msg)
                return redirect('phonebook:profile_view', profile.user.username)

        if (request.user.is_authenticated() and profile.is_vouchable(request.user.userprofile)):

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

    data['shown_user'] = profile.user
    data['profile'] = profile
    data['access_groups'] = profile.get_annotated_access_groups()
    data['tags'] = profile.get_annotated_tags()
    data['abuse_form'] = abuse_form
    data['alternate_identities'] = profile.identity_profiles.filter(primary_contact_identity=False)

    # Only show pending groups if user is looking at their own profile,
    # or current user is a superuser
    if not (request.user.is_authenticated() and
            (request.user.username == username or request.user.is_superuser)):
        data['access_groups'] = [grp for grp in data['access_groups']
                                 if not (grp.pending or grp.pending_terms)]
        data['tags'] = [tag for tag in data['tags'] if not (tag.pending or tag.pending_terms)]

    return render(request, 'phonebook/profile.html', data)


@allow_unvouched
@never_cache
def edit_profile(request):
    """Edit user profile view."""
    # Don't use request.user
    user = User.objects.get(pk=request.user.id)
    profile = user.userprofile
    user_groups = profile.groups.all().order_by('name')
    idp_profiles = IdpProfile.objects.filter(profile=profile)
    idp_primary_profile = get_object_or_none(IdpProfile, profile=profile, primary=True)
    accounts_qs = ExternalAccount.objects.exclude(type=ExternalAccount.TYPE_EMAIL)

    sections = {
        'registration_section': ['user_form', 'registration_form'],
        'basic_section': ['user_form', 'basic_information_form'],
        'groups_section': ['groups_privacy_form'],
        'skills_section': ['skills_form'],
        'idp_section': ['idp_profile_formset'],
        'languages_section': ['language_privacy_form', 'language_formset'],
        'accounts_section': ['accounts_formset'],
        'location_section': ['location_form'],
        'irc_section': ['irc_form'],
        'contribution_section': ['contribution_form'],
        'tshirt_section': ['tshirt_form'],
    }

    curr_sect = next((s for s in sections.keys() if s in request.POST), None)

    def get_request_data(form):
        if curr_sect and form in sections[curr_sect]:
            return request.POST
        return None

    ctx = {}
    ctx['user_form'] = forms.UserForm(get_request_data('user_form'), instance=user)
    ctx['registration_form'] = forms.RegisterForm(get_request_data('registration_form'),
                                                  request.FILES or None,
                                                  instance=profile)
    basic_information_data = get_request_data('basic_information_form')
    ctx['basic_information_form'] = forms.BasicInformationForm(basic_information_data,
                                                               request.FILES or None,
                                                               instance=profile)
    ctx['accounts_formset'] = forms.AccountsFormset(get_request_data('accounts_formset'),
                                                    instance=profile,
                                                    queryset=accounts_qs)
    ctx['location_form'] = forms.LocationForm(get_request_data('location_form'), instance=profile)
    ctx['language_formset'] = forms.LanguagesFormset(get_request_data('language_formset'),
                                                     instance=profile,
                                                     locale=request.locale)
    language_privacy_data = get_request_data('language_privacy_form')
    ctx['language_privacy_form'] = forms.LanguagesPrivacyForm(language_privacy_data,
                                                              instance=profile)
    ctx['skills_form'] = forms.SkillsForm(get_request_data('skills_form'), instance=profile)
    ctx['contribution_form'] = forms.ContributionForm(get_request_data('contribution_form'),
                                                      instance=profile)
    ctx['tshirt_form'] = forms.TshirtForm(get_request_data('tshirt_form'), instance=profile)
    ctx['groups_privacy_form'] = forms.GroupsPrivacyForm(get_request_data('groups_privacy_form'),
                                                         instance=profile)
    ctx['irc_form'] = forms.IRCForm(get_request_data('irc_form'), instance=profile)
    ctx['idp_profile_formset'] = forms.IdpProfileFormset(get_request_data('idp_profile_formset'),
                                                         instance=profile,
                                                         queryset=idp_profiles)
    ctx['idp_primary_profile'] = idp_primary_profile

    ctx['autocomplete_form_media'] = ctx['registration_form'].media + ctx['skills_form'].media
    forms_valid = True
    if request.POST:
        if not curr_sect:
            raise Http404
        curr_forms = map(lambda x: ctx[x], sections[curr_sect])
        forms_valid = all(map(lambda x: x.is_valid(), curr_forms))
        if forms_valid:
            old_username = request.user.username
            for f in curr_forms:
                f.save()

            # Spawn task to check for spam
            if not profile.can_vouch:
                params = {
                    'instance_id': profile.id,
                    'user_ip': request.META.get('REMOTE_ADDR'),
                    'user_agent': request.META.get('HTTP_USER_AGENT'),
                    'referrer': request.META.get('HTTP_REFERER'),
                    'comment_author': profile.full_name,
                    'comment_author_email': profile.email,
                    'comment_content': profile.bio
                }

                check_spam_account.delay(**params)

            next_section = request.GET.get('next')
            next_url = urlparams(reverse('phonebook:profile_edit'), next_section)
            if curr_sect == 'registration_section':
                settings_url = reverse('phonebook:profile_edit')
                settings_link = '<a href="{0}">settings</a>'.format(settings_url)
                msg = _(u'Your registration is complete. '
                        u'Feel free to visit the {0} page to add '
                        u'additional information to your profile.'.format(settings_link))
                messages.info(request, mark_safe(msg))
                redeem_invite(profile, request.session.get('invite-code'))
                next_url = reverse('phonebook:profile_view', args=[user.username])
            elif user.username != old_username:
                msg = _(u'You changed your username; '
                        u'please note your profile URL has also changed.')
                messages.info(request, _(msg))
            return HttpResponseRedirect(next_url)

    ctx.update({
        'user_groups': user_groups,
        'profile': request.user.userprofile,
        'vouch_threshold': settings.CAN_VOUCH_THRESHOLD,
        'appsv2': profile.apps.filter(enabled=True),
        'forms_valid': forms_valid
    })

    return render(request, 'phonebook/edit_profile.html', ctx)


@allow_unvouched
@never_cache
def delete_identity(request, identity_pk):
    """Delete alternate email address."""
    user = User.objects.get(pk=request.user.id)
    profile = user.userprofile

    # Only email owner can delete emails
    idp_query = IdpProfile.objects.filter(profile=profile, pk=identity_pk)
    if not idp_query.exists():
        raise Http404()

    idp_query = idp_query.filter(primary=False, primary_contact_identity=False)
    if idp_query.exists():
        idp_type = idp_query[0].get_type_display()
        idp_query.delete()
        send_userprofile_to_cis.delay(profile.pk)
        msg = _(u'Identity {0} successfully deleted.'.format(idp_type))
        messages.success(request, msg)
        return redirect('phonebook:profile_edit')

    # We are trying to delete the primary identity, politely ignore the request
    msg = _(u'Sorry the requested Identity cannot be deleted.')
    messages.error(request, msg)
    return redirect('phonebook:profile_edit')


@allow_unvouched
@never_cache
def change_primary_contact_identity(request, identity_pk):
    """Change primary email address."""
    user = User.objects.get(pk=request.user.id)
    profile = user.userprofile
    alternate_identities = IdpProfile.objects.filter(profile=profile)

    # Only email owner can change primary email
    if not alternate_identities.filter(pk=identity_pk).exists():
        raise Http404()

    if alternate_identities.filter(primary_contact_identity=True).exists():
        alternate_identities.filter(pk=identity_pk).update(primary_contact_identity=True)
        alternate_identities.exclude(pk=identity_pk).update(primary_contact_identity=False)

        msg = _(u'Primary Contact Identity successfully updated.')
        messages.success(request, msg)

    return redirect('phonebook:profile_edit')


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
@cache_control(public=True, must_revalidate=True, max_age=3600 * 24 * 7)  # 1 week.
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


def apikeys(request):
    profile = request.user.userprofile
    apikey_request_form = forms.APIKeyRequestForm(
        request.POST or None,
        instance=APIv2App(enabled=True, owner=profile)
    )

    if apikey_request_form.is_valid():
        apikey_request_form.save()
        msg = _(u'API Key generated successfully.')
        messages.success(request, msg)
        return redirect('phonebook:apikeys')

    data = {
        'appsv2': profile.apps.filter(enabled=True),
        'apikey_request_form': apikey_request_form,
    }
    return render(request, 'phonebook/apikeys.html', data)


def delete_apikey(request, api_pk):
    api_key = get_object_or_404(APIv2App, pk=api_pk, owner=request.user.userprofile)
    api_key.delete()
    messages.success(request, _('API key successfully deleted.'))
    return redirect('phonebook:apikeys')


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


@require_POST
@csrf_exempt
@allow_public
def capture_csp_violation(request):
    data = client.get_data_from_request(request)
    data.update({
        'level': logging.INFO,
        'logger': 'CSP',
    })
    try:
        csp_data = json.loads(request.body)
    except ValueError:
        # Cannot decode CSP violation data, ignore
        return HttpResponseBadRequest('Invalid CSP Report')

    try:
        blocked_uri = csp_data['csp-report']['blocked-uri']
    except KeyError:
        # Incomplete CSP report
        return HttpResponseBadRequest('Incomplete CSP Report')

    client.captureMessage(
        message='CSP Violation: {}'.format(blocked_uri),
        data=data)

    return HttpResponse('Captured CSP violation, thanks for reporting.')


# Django haystack
@allow_public
class PhonebookSearchView(SearchView):
    form_class = forms.PhonebookSearchForm
    template_name = 'phonebook/search.html'

    def get_queryset(self):
        sqs = super(PhonebookSearchView, self).get_queryset()
        return sqs

    def form_invalid(self, form):
        context = self.get_context_data(**{
            self.form_name: form,
            'object_list': EmptySearchQuerySet()
        })
        return self.render_to_response(context)

    def get_form_kwargs(self):
        """Pass the request.user to the form's kwargs."""
        kwargs = {'initial': self.get_initial()}
        if self.request.method == 'GET':
            kwargs.update({
                'data': self.request.GET
            })
        kwargs.update({'searchqueryset': self.get_queryset()})
        kwargs['request'] = self.request
        # pass the parameters from the url
        kwargs.update(self.kwargs)
        return kwargs

    def get_context_data(self, **kwargs):
        """Override method to pass more context data in the template."""
        context_data = super(PhonebookSearchView, self).get_context_data(**kwargs)
        context_data['functional_areas'] = Group.get_functional_areas()
        context_data['show_pagination'] = context_data['is_paginated']
        context_data['search_form'] = context_data['form']
        context_data['country'] = self.kwargs.get('country')
        context_data['region'] = self.kwargs.get('region')
        context_data['city'] = self.kwargs.get('city')
        return context_data


# Verify additional identities
class VerifyIdentityView(OIDCAuthenticationRequestView):

    def __init__(self, *args, **kwargs):
        """Override the init method to dynamically pass a different client_id."""
        self.OIDC_RP_VERIFICATION_CLIENT_ID = (
            import_from_settings('OIDC_RP_VERIFICATION_CLIENT_ID')
        )
        super(VerifyIdentityView, self).__init__(*args, **kwargs)

    def get(self, request):
        """OIDC client authentication initialization HTTP endpoint.

        This is based on the mozilla-django-oidc library
        """
        state = get_random_string(import_from_settings('OIDC_STATE_SIZE', 32))
        redirect_field_name = import_from_settings('OIDC_REDIRECT_FIELD_NAME', 'next')

        params = {
            'response_type': 'code',
            'scope': import_from_settings('OIDC_RP_SCOPES', 'openid email'),
            'client_id': self.OIDC_RP_VERIFICATION_CLIENT_ID,
            'redirect_uri': absolutify(
                request,
                nonprefixed_url('phonebook:verify_identity_callback')
            ),
            'state': state,
            'prompt': settings.OIDC_PROMPT
        }

        if import_from_settings('OIDC_USE_NONCE', True):
            nonce = get_random_string(import_from_settings('OIDC_NONCE_SIZE', 32))
            params.update({
                'nonce': nonce
            })
            request.session['oidc_verify_nonce'] = nonce

        # Add parameter to disable silent authentication and the LDAP check for AUTO_VOUCH_DOMAINS
        # This will allow users to verify AUTO_VOUCH_DOMAINS as contact identities
        params['account_linking'] = settings.OIDC_ACCOUNT_LINKING

        request.session['oidc_verify_state'] = state
        request.session['oidc_login_next'] = get_next_url(request, redirect_field_name)

        query = urlencode(params)
        redirect_url = '{url}?{query}'.format(url=self.OIDC_OP_AUTH_ENDPOINT, query=query)
        return HttpResponseRedirect(redirect_url)


class VerifyIdentityCallbackView(View):

    def __init__(self, *args, **kwargs):
        """Initialize settings."""
        self.OIDC_OP_TOKEN_ENDPOINT = import_from_settings('OIDC_OP_TOKEN_ENDPOINT')
        self.OIDC_OP_USER_ENDPOINT = import_from_settings('OIDC_OP_USER_ENDPOINT')
        self.OIDC_RP_VERIFICATION_CLIENT_ID = (
            import_from_settings('OIDC_RP_VERIFICATION_CLIENT_ID')
        )
        self.OIDC_RP_VERIFICATION_CLIENT_SECRET = (
            import_from_settings('OIDC_RP_VERIFICATION_CLIENT_SECRET')
        )

    def get(self, request):
        """Callback handler for OIDC authorization code flow.

        This is based on the mozilla-django-oidc library.
        This callback is used to verify the identity added by the user.
        Users are already logged in and we do not care about authentication.
        The JWT token is used to prove the identity of the user.
        """

        profile = request.user.userprofile
        # This is a difference nonce than the one used to login!
        nonce = request.session.get('oidc_verify_nonce')
        if nonce:
            # Make sure that nonce is not used twice
            del request.session['oidc_verify_nonce']

        # Check for all possible errors and display a message to the user.
        errors = [
            'code' not in request.GET,
            'state' not in request.GET,
            'oidc_verify_state' not in request.session,
            request.GET['state'] != request.session['oidc_verify_state']
        ]
        if any(errors):
            msg = 'Something went wrong, account verification failed.'
            messages.error(request, msg)
            return redirect('phonebook:profile_edit')

        token_payload = {
            'client_id': self.OIDC_RP_VERIFICATION_CLIENT_ID,
            'client_secret': self.OIDC_RP_VERIFICATION_CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': request.GET['code'],
            'redirect_uri': absolutify(
                self.request,
                nonprefixed_url('phonebook:verify_identity_callback')
            ),
        }
        response = requests.post(self.OIDC_OP_TOKEN_ENDPOINT,
                                 data=token_payload,
                                 verify=import_from_settings('OIDC_VERIFY_SSL', True))
        response.raise_for_status()
        token_response = response.json()
        id_token = token_response.get('id_token')

        # Verify JWT
        jws = JWS.from_compact(force_bytes(id_token))
        jwk = JWK.load(smart_bytes(self.OIDC_RP_VERIFICATION_CLIENT_SECRET))
        verified_token = None
        if jws.verify(jwk):
            verified_token = jws.payload

        # Create the new Identity Profile.
        if verified_token:
            user_info = json.loads(verified_token)
            email = user_info['email']

            if not user_info.get('email_verified'):
                msg = 'Account verification failed: Email is not verified.'
                messages.error(request, msg)
                return redirect('phonebook:profile_edit')

            user_q = {
                'auth0_user_id': user_info['sub'],
                'email': email
            }

            # Check that the identity doesn't exist in another Identity profile
            # or in another mozillians profile
            error_msg = ''
            if IdpProfile.objects.filter(**user_q).exists():
                error_msg = 'Account verification failed: Identity already exists.'
            elif User.objects.filter(email__iexact=email).exclude(pk=profile.user.pk).exists():
                error_msg = 'The email in this identity is used by another user.'
            if error_msg:
                messages.error(request, error_msg)
                next_url = self.request.session.get('oidc_login_next', None)
                return HttpResponseRedirect(next_url or reverse('phonebook:profile_edit'))

            # Save the new identity to the IdpProfile
            user_q['profile'] = profile
            idp, created = IdpProfile.objects.get_or_create(**user_q)

            current_idp = get_object_or_none(IdpProfile, profile=profile, primary=True)
            # The new identity is stronger than the one currently used. Let's swap
            append_msg = ''
            # We need to check for equality too in the case a user updates the primary email in
            # the same identity (matching auth0_user_id). If there is an addition of the same type
            # we are not swapping login identities
            if ((current_idp and current_idp.type < idp.type) or
                (current_idp and current_idp.auth0_user_id == idp.auth0_user_id) or
                    (not current_idp and created and idp.type >= IdpProfile.PROVIDER_GITHUB)):
                IdpProfile.objects.filter(profile=profile).exclude(pk=idp.pk).update(primary=False)
                idp.primary = True
                idp.save()
                # Also update the primary email of the user
                update_email_in_basket(profile.user.email, idp.email)
                User.objects.filter(pk=profile.user.id).update(email=idp.email)
                append_msg = ' You need to use this identity the next time you will login.'

            send_userprofile_to_cis.delay(profile.pk)
            if created:
                msg = 'Account successfully verified.'
                if append_msg:
                    msg += append_msg
                messages.success(request, msg)
            else:
                msg = 'Account verification failed: Identity already exists.'
                messages.error(request, msg)

        next_url = self.request.session.get('oidc_login_next', None)
        return HttpResponseRedirect(next_url or reverse('phonebook:profile_edit'))


@waffle_flag('delete-idp-profiles-qa')
@allow_unvouched
@never_cache
def delete_idp_profiles(request):
    """QA helper: Delete IDP profiles for request.user"""
    request.user.userprofile.idp_profiles.all().delete()
    messages.warning(request, 'Identities deleted.')
    return redirect('phonebook:profile_edit')
