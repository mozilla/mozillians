import json

from collections import defaultdict

from django.http import JsonResponse
from django.conf import settings
from django.contrib import messages
from django.core.paginator import EmptyPage, Paginator, PageNotAnInteger
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_control, never_cache
from django.views.decorators.http import require_POST
from django.utils.translation import ugettext as _

from dal import autocomplete
from waffle.decorators import waffle_flag, waffle_switch

from mozillians.common.decorators import allow_unvouched
from mozillians.common.templatetags.helpers import get_object_or_none, urlparams
from mozillians.common.urlresolvers import reverse
from mozillians.groups import forms
from mozillians.groups.models import Group, GroupMembership, Invite, Skill
from mozillians.groups.tasks import (notify_curators_invitation_accepted,
                                     notify_curators_invitation_rejected,
                                     notify_redeemer_invitation,
                                     notify_redeemer_invitation_invalid,
                                     notify_membership_renewal)
from mozillians.users.models import UserProfile


def _list_groups(request, template, query, context={}):
    """Lists groups from given query."""

    sort_form = forms.SortForm(request.GET)
    show_pagination = False

    if sort_form.is_valid():
        query = query.order_by(sort_form.cleaned_data['sort'], 'name')
    else:
        query = query.order_by('name')

    paginator = Paginator(query, settings.ITEMS_PER_PAGE)

    page = request.GET.get('page', 1)
    try:
        groups = paginator.page(page)
    except PageNotAnInteger:
        groups = paginator.page(1)
    except EmptyPage:
        groups = paginator.page(paginator.num_pages)

    if paginator.count > settings.ITEMS_PER_PAGE:
        show_pagination = True

    data = {
        'groups': groups,
        'page': page,
        'sort_form': sort_form,
        'show_pagination': show_pagination
    }

    data.update(context)
    return render(request, template, data)


def index_groups(request):
    """Lists all public groups (in use) on Mozillians.

    Doesn't list functional areas, invisible groups, and groups with
    no vouched members
    """

    group_form = forms.GroupCreateForm(request.POST or None)
    if group_form.is_valid():
        group = group_form.save()
        group.curators.add(request.user.userprofile)
        group.add_member(request.user.userprofile, GroupMembership.MEMBER)
        return redirect(reverse('groups:group_edit', args=[group.url]))

    query = Group.get_non_functional_areas()
    template = 'groups/index_groups.html'
    context = {
        'group_form': group_form
    }
    return _list_groups(request, template, query, context)


def index_skills(request):
    """Lists all public skills (in use) on Mozillians."""
    query = Skill.objects.filter(members__is_vouched=True)
    template = 'groups/index_skills.html'
    return _list_groups(request, template, query)


def index_functional_areas(request):
    """Lists all functional areas."""
    query = Group.get_functional_areas()
    template = 'groups/index_areas.html'
    return _list_groups(request, template, query)


@allow_unvouched
@cache_control(must_revalidate=True, max_age=3600)
def search(request, searched_object=Group):
    """Simple wildcard search for a group using a GET parameter.

    Used for group/skill auto-completion.

    """
    term = request.GET.get('term', None)
    if request.is_ajax() and term:
        groups = searched_object.search(term).values_list('name', flat=True)
        return HttpResponse(json.dumps(list(groups)),
                            content_type='application/json')

    return HttpResponseBadRequest()


@never_cache
def show(request, url, alias_model, template):
    """List all members in this group."""
    group_alias = get_object_or_404(alias_model, url=url)
    if group_alias.alias.url != url:
        return redirect('groups:show_group', url=group_alias.alias.url)

    is_curator = False
    is_manager = request.user.userprofile.is_manager
    is_pending = False
    show_delete_group_button = False
    membership_filter_form = forms.MembershipFilterForm(request.GET)

    group = group_alias.alias
    profile = request.user.userprofile
    in_group = group.has_member(profile)
    memberships = group.members.all()
    data = {}

    if isinstance(group, Group):

        # Has the user accepted the group terms
        if group.terms:
            membership = get_object_or_none(GroupMembership, group=group, userprofile=profile,
                                            status=GroupMembership.PENDING_TERMS)
            if membership:
                return redirect(reverse('groups:review_terms', args=[group.url]))

        # Is this user's membership pending?
        is_pending = group.has_pending_member(profile)

        is_curator = is_manager or (request.user.userprofile in group.curators.all())

        # initialize the form only when the group is moderated and user is curator of the group
        if (is_curator and (group.accepting_new_members == Group.REVIEWED or
                            group.accepting_new_members == Group.CLOSED)):
            membership_filter_form = forms.MembershipFilterForm(request.GET)
        else:
            membership_filter_form = None

        if is_curator:
            statuses = [GroupMembership.MEMBER, GroupMembership.PENDING,
                        GroupMembership.PENDING_TERMS]
            q_args = {'status__in': statuses}
            if membership_filter_form and membership_filter_form.is_valid():
                filtr = membership_filter_form.cleaned_data['filtr']
                if filtr == 'members':
                    statuses = [GroupMembership.MEMBER]
                elif filtr == 'pending_members':
                    statuses = [GroupMembership.PENDING]
                elif filtr == 'pending_terms':
                    statuses = [GroupMembership.PENDING_TERMS]

                q_args.update({'status__in': statuses})

                if filtr == 'needs_renewal':
                    q_args = {'needs_renewal': True}

            memberships = group.groupmembership_set.filter(**q_args)

            # Curators can delete their group if there are no other members.
            show_delete_group_button = is_curator and group.members.all().count() == 1

        else:
            # only show full members, or this user
            memberships = group.groupmembership_set.filter(Q(status=GroupMembership.MEMBER) |
                                                           Q(userprofile=profile))

        invitation = get_object_or_none(Invite, redeemer=profile, group=group, accepted=False)
        data.update(invitation=invitation)
        # Order by UserProfile.Meta.ordering
        memberships = memberships.order_by('userprofile')

        # Find the most common skills of the group members.
        # Order by popularity in the group.
        shared_skill_ids = (group.members.filter(groupmembership__status=GroupMembership.MEMBER)
                            .values_list('skills', flat=True))

        count_skills = defaultdict(int)
        for skill_id in shared_skill_ids:
            count_skills[skill_id] += 1
        common_skills_ids = [k for k, _ in sorted(count_skills.items(),
                                                  key=lambda x: x[1],
                                                  reverse=True)
                             if count_skills[k] > 1]

        # Translate ids to Skills preserving order.
        skills = [Skill.objects.get(id=skill_id) for skill_id in common_skills_ids if skill_id]

        data.update(skills=skills, membership_filter_form=membership_filter_form)

    page = request.GET.get('page', 1)
    paginator = Paginator(memberships, settings.ITEMS_PER_PAGE)

    try:
        people = paginator.page(page)
    except PageNotAnInteger:
        people = paginator.page(1)
    except EmptyPage:
        people = paginator.page(paginator.num_pages)

    show_pagination = paginator.count > settings.ITEMS_PER_PAGE

    extra_data = dict(
        people=people,
        group=group,
        in_group=in_group,
        is_curator=is_curator,
        is_pending=is_pending,
        show_pagination=show_pagination,
        show_delete_group_button=show_delete_group_button,
        show_join_button=group.user_can_join(request.user.userprofile),
        show_leave_button=group.user_can_leave(request.user.userprofile),
        members=group.member_count,
    )

    data.update(extra_data)

    return render(request, template, data)


def remove_member(request, url, user_pk, status=None):
    group = get_object_or_404(Group, url=url)
    profile_to_remove = get_object_or_404(UserProfile, pk=user_pk)
    this_userprofile = request.user.userprofile
    is_curator = (this_userprofile in group.curators.all())
    is_manager = request.user.userprofile.is_manager
    group_url = reverse('groups:show_group', args=[group.url])
    next_url = request.REQUEST.get('next_url', group_url)

    # TODO: this duplicates some of the logic in Group.user_can_leave(), but we
    # want to give the user a message that's specific to the reason they can't leave.
    # Can we make this DRYer?

    # You can remove yourself, if group allows it. Curator and superuser can remove anyone.
    if not (is_curator or is_manager):
        if not group.members_can_leave:
            messages.error(request, _('This group does not allow members to remove themselves.'))
            return redirect(next_url)
        if profile_to_remove != this_userprofile:
            raise Http404()

    # Curators cannot be removed, only by themselves and if there is another curator.
    curators = group.curators.all()
    if (profile_to_remove in curators and curators.count() <= 1 and
            profile_to_remove != this_userprofile):
        messages.error(request, _('The group needs at least one curator.'))
        return redirect(next_url)

    if request.method == 'POST':
        group.remove_member(profile_to_remove, status=status,
                            send_email=(profile_to_remove != this_userprofile))
        if profile_to_remove in curators:
            group.curators.remove(profile_to_remove)
        if this_userprofile == profile_to_remove:
            messages.info(request, _('You have been removed from this group.'))
        else:
            messages.info(request, _('The group member has been removed.'))
        return redirect(next_url)

    # Display confirmation page
    context = {
        'group': group,
        'profile': profile_to_remove,
        'next_url': next_url
    }
    return render(request, 'groups/confirm_remove_member.html', context)


@require_POST
def confirm_member(request, url, user_pk):
    """
    Add a member to a group who has requested membership.
    """
    group = get_object_or_404(Group, url=url)
    profile = get_object_or_404(UserProfile, pk=user_pk)
    is_curator = (request.user.userprofile in group.curators.all())
    is_manager = request.user.userprofile.is_manager
    group_url = reverse('groups:show_group', args=[group.url])
    next_url = request.REQUEST.get('next_url', group_url)

    if not (is_curator or is_manager):
        raise Http404()
    try:
        membership = GroupMembership.objects.get(group=group, userprofile=profile)
    except GroupMembership.DoesNotExist:
        messages.error(request, _('This user has not requested membership in this group.'))
    else:
        if membership.status == GroupMembership.MEMBER and not membership.needs_renewal:
            messages.error(request, _('This user is already a member of this group.'))
        else:
            status = GroupMembership.MEMBER
            if group.terms:
                status = GroupMembership.PENDING_TERMS
            group.add_member(profile, status=status)
            if membership.needs_renewal:
                messages.info(request, _('The membership of the user has been renewed.'))
            else:
                messages.info(request, _('This user has been added as a member of this group.'))
    return redirect(next_url)


def edit(request, url, alias_model, template):
    return render(request, alias_model, template)


def review_terms(request, url):
    """Review group terms page."""
    group = get_object_or_404(Group, url=url)
    if not group.terms:
        return redirect(reverse('groups:show_group', args=[group.url]))

    membership = get_object_or_404(GroupMembership, group=group,
                                   userprofile=request.user.userprofile,
                                   status=GroupMembership.PENDING_TERMS)

    membership_form = forms.TermsReviewForm(request.POST or None)
    if membership_form.is_valid():
        if membership_form.cleaned_data['terms_accepted'] == 'True':
            group.add_member(request.user.userprofile, GroupMembership.MEMBER)
        else:
            membership.delete()
        return redirect(reverse('groups:show_group', args=[group.url]))

    ctx = {
        'group': group,
        'membership_form': membership_form
    }

    return render(request, 'groups/terms.html', ctx)


@require_POST
def join_group(request, url):
    """User request to join group."""
    group = get_object_or_404(Group, url=url)
    profile_to_add = request.user.userprofile

    # TODO: this duplicates some of the logic in Group.user_can_join(), but we
    # want to give the user a message that's specific to the reason they can't join.
    # Can we make this DRYer?

    if group.has_member(profile_to_add):
        messages.error(request, _('You are already in this group.'))
    elif group.has_pending_member(profile_to_add):
        messages.error(request, _('Your request to join this group is still pending.'))
    elif group.accepting_new_members == Group.CLOSED:
        messages.error(request, _('This group is not accepting requests to join.'))
    else:
        if group.accepting_new_members == Group.OPEN:
            status = GroupMembership.MEMBER
            messages.info(request, _('You have been added to this group.'))
            if group.terms:
                status = GroupMembership.PENDING_TERMS
        elif group.accepting_new_members == Group.REVIEWED:
            status = GroupMembership.PENDING
            messages.info(request, _('Your membership request has been sent '
                                     'to the group curator(s).'))

        group.add_member(profile_to_add, status=status)

    return redirect(reverse('groups:show_group', args=[group.url]))


@require_POST
def toggle_skill_subscription(request, url):
    """Toggle the current user's membership of a group."""
    skill = get_object_or_404(Skill, url=url)
    profile = request.user.userprofile

    if profile.skills.filter(id=skill.id).exists():
        profile.skills.remove(skill)
    else:
        profile.skills.add(skill)

    return redirect(reverse('groups:show_skill', args=[skill.url]))


@require_POST
def group_delete(request, url):
    profile = request.user.userprofile
    # Get the group to delete
    group = get_object_or_404(Group, url=url)
    # Only a group curator is allowed to delete a group
    is_curator = profile in group.curators.all()
    if not is_curator and not profile.is_manager:
        messages.error(request, _('You must be a curator to delete a group'))
        return redirect(reverse('groups:show_group', args=[group.url]))
    # Cannot delete if anyone else is in it
    if group.members.all().count() != 1:
        messages.error(request, _('You cannot delete a group if anyone else is in it.'))
        return redirect(reverse('groups:show_group', args=[group.url]))
    # Go to it
    group.delete()
    messages.info(request, _('Group %s has been deleted') % group.name)
    return redirect(reverse('groups:index_groups'))


@never_cache
def group_edit(request, url=None):
    """Add or edit a group. (if there is a url we are editing)"""

    profile = request.user.userprofile
    is_manager = request.user.userprofile.is_manager
    invites = None
    forms_valid = True
    group_forms = {}
    form_key = None
    show_delete_group_button = False

    if not url:
        return redirect(reverse('groups:index_groups'))

    # Get the group to edit
    group = get_object_or_404(Group, url=url)
    # Only a group curator or an admin is allowed to edit a group
    is_curator = profile in group.curators.all()
    is_manager = request.user.userprofile.is_manager
    if not (is_curator or is_manager):
        messages.error(request, _('You must be a curator or an admin to edit a group'))
        return redirect(reverse('groups:show_group', args=[group.url]))

    invites = group.invites.filter(groups_invited__accepted=False)
    show_delete_group_button = is_curator and group.members.all().count() == 1

    # Prepare the forms for rendering
    group_forms['basic_form'] = forms.GroupBasicForm
    group_forms['curator_form'] = forms.GroupCuratorsForm
    group_forms['terms_expiration_form'] = forms.GroupTermsExpirationForm
    group_forms['invite_form'] = forms.GroupInviteForm
    group_forms['admin_form'] = forms.GroupAdminForm
    group_forms['criteria_form'] = forms.GroupCriteriaForm
    group_forms['email_form'] = forms.GroupCustomEmailForm

    def _init_group_forms(request, group_forms):
        form_args = {
            'data': None,
            'instance': group,
            'request': request
        }
        key = None

        if request.POST:
            form_args['data'] = request.POST
            key, form = next(((k, v(**form_args)) for k, v in group_forms.items()
                              if k in request.POST), (None, None))
            if key and form:
                group_forms[key] = form

        # Initialize the rest of the forms with non-POST data
        form_args['data'] = None
        for k in group_forms.keys():
            if k != key:
                group_forms[k] = group_forms[k](**form_args)
        return key

    form_key = _init_group_forms(request, group_forms)

    form = group_forms[form_key] if form_key else None
    if form and form.is_bound and form.is_valid():
        form.save()
        next_section = request.GET.get('next')
        next_url = urlparams(reverse('groups:group_edit', args=[group.url]), next_section)
        return HttpResponseRedirect(next_url)
    elif request.POST:
        forms_valid = False

    context = {
        'group': group if url else None,
        'invites': invites if group else None,
        'forms_valid': forms_valid,
        'user_is_curator': is_curator,
        'user_is_manager': is_manager,
        'show_delete_group_button': show_delete_group_button
    }
    context.update(group_forms)
    return render(request, 'groups/edit_group.html', context)


class SkillsAutocomplete(autocomplete.Select2QuerySetView):

    def __init__(self, *args, **kwargs):
        super(SkillsAutocomplete, self).__init__(*args, **kwargs)
        self.cached_skills = list(Skill.objects.all().values_list('name', flat=True))

    def get_queryset(self):

        qs = Skill.objects.all()
        if self.q:
            qs = qs.filter(name__istartswith=self.q)
        return qs

    def render_to_response(self, context):
        """Override base render_to_response.

        Return a JSON response in Select2 format."""
        create_option = []

        q = self.request.GET.get('q', None)

        if (self.request.GET.get('create', None) == 'true' and q and
                q.lower() not in self.cached_skills):
            create_option = [{
                'id': q,
                'text': 'Create "%s"' % q
            }]

        data = {
            'results': self.get_results(context) + create_option,
            'more': self.has_more(context)
        }

        return JsonResponse(data)


# Invite views
def delete_invite(request, invite_pk):
    """Delete an invite to join a group."""

    invite = get_object_or_404(Invite, pk=invite_pk)
    group = invite.group

    if (group.curators.filter(id=request.user.userprofile.id).exists() or
            request.user.userprofile.is_manager):
        redeemer = invite.redeemer
        invite.delete()
        notify_redeemer_invitation_invalid.delay(redeemer.pk, group.pk)
        msg = _(u'The invitation to {0} has been successfully revoked.').format(redeemer)
        messages.success(request, msg)
        next_section = request.GET.get('next')
        next_url = urlparams(reverse('groups:group_edit', args=[group.url]), next_section)
        return HttpResponseRedirect(next_url)
    raise Http404()


@never_cache
def accept_reject_invitation(request, invite_pk, action):
    """Accept or reject group invitation."""

    redeemer = request.user.userprofile
    invite = get_object_or_404(Invite, pk=invite_pk, redeemer=redeemer)
    if action == 'accept':
        if invite.group.terms:
            invite.group.add_member(redeemer, GroupMembership.PENDING_TERMS)
        else:
            invite.group.add_member(redeemer, GroupMembership.MEMBER)
        invite.accepted = True
        invite.save()
        notify_curators_invitation_accepted.delay(invite.pk)
    else:
        notify_curators_invitation_rejected.delay(redeemer.pk, invite.inviter.pk, invite.group.pk)
        invite.delete()

    return redirect(reverse('groups:show_group', args=[invite.group.url]))


@never_cache
def send_invitation_email(request, invite_pk):
    """Send group invitation email."""

    invite = get_object_or_404(Invite, pk=invite_pk)
    is_curator = invite.group.curators.filter(pk=request.user.userprofile.pk).exists()
    is_manager = request.user.userprofile.is_manager

    if not (is_curator or is_manager):
        raise Http404

    notify_redeemer_invitation.delay(invite.pk, invite.group.invite_email_text)
    msg = _(u'Invitation to {0} has been sent successfully.'.format(invite.redeemer))
    messages.success(request, msg)
    next_section = request.GET.get('next')
    next_url = urlparams(reverse('groups:group_edit', args=[invite.group.url]), next_section)

    return HttpResponseRedirect(next_url)


@never_cache
@waffle_flag('force_group_invalidation', '404')
def force_group_invalidation(request, url, alias_model, template=''):
    """View to help test different scenarios.

    Forces an immediate invalidation in the case that a group is
    set to expire its memberships.
    """
    group_alias = get_object_or_404(alias_model, url=url)
    group = group_alias.alias
    is_curator = group.curators.filter(id=request.user.userprofile.pk).exists()
    if group.invalidation_days and is_curator:

        curator_ids = group.curators.all().values_list('id', flat=True)
        memberships = group.groupmembership_set.exclude(userprofile__id__in=curator_ids)

        for member in memberships:
            status = None
            if group.accepting_new_members != Group.OPEN:
                status = GroupMembership.PENDING
            group.remove_member(member.userprofile, status=status)
    else:
        raise Http404

    return redirect(reverse('groups:show_group', args=[group.url]))


@never_cache
@waffle_switch('test_membership_renewal_notification')
def membership_renewal_notification(request):
    """View to help test membership renewal notification

    Manually spawn a task to send membership renewal notifications to the users.
    """
    notify_membership_renewal.apply_async()
    return redirect(reverse('groups:index_groups'))
