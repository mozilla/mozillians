import json

from collections import defaultdict

from django.conf import settings
from django.contrib import messages
from django.core.paginator import EmptyPage, Paginator, PageNotAnInteger
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_control, never_cache
from django.views.decorators.http import require_POST

from funfactory.urlresolvers import reverse
from mozillians.users.models import UserProfile
from tower import ugettext as _

from mozillians.common.decorators import allow_unvouched
from mozillians.common.helpers import get_object_or_none
from mozillians.groups.forms import (GroupForm, TermsReviewForm,
                                     MembershipFilterForm, SortForm,
                                     SuperuserGroupForm)
from mozillians.groups.models import Group, Skill, GroupMembership


def _list_groups(request, template, query):
    """Lists groups from given query."""

    sort_form = SortForm(request.GET)
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

    data = dict(groups=groups, page=page, sort_form=sort_form, show_pagination=show_pagination)
    return render(request, template, data)


def index_groups(request):
    """Lists all public groups (in use) on Mozillians.

    Doesn't list functional areas, invisible groups, and groups with
    no vouched members
    """
    query = Group.get_non_functional_areas()
    template = 'groups/index_groups.html'
    return _list_groups(request, template, query)


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
    membership_filter_form = MembershipFilterForm(request.GET)

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
        if is_curator and group.accepting_new_members == 'by_request':
            membership_filter_form = MembershipFilterForm(request.GET)
        else:
            membership_filter_form = None

        if is_curator:
            statuses = [GroupMembership.MEMBER, GroupMembership.PENDING]
            if membership_filter_form and membership_filter_form.is_valid():
                filtr = membership_filter_form.cleaned_data['filtr']
                if filtr == 'members':
                    statuses = [GroupMembership.MEMBER]
                elif filtr == 'pending_members':
                    statuses = [GroupMembership.PENDING]

            memberships = group.groupmembership_set.filter(status__in=statuses)

            # Curators can delete their group if there are no other members.
            show_delete_group_button = is_curator and group.members.all().count() == 1

        else:
            # only show full members, or this user
            memberships = group.groupmembership_set.filter(
                Q(status=GroupMembership.MEMBER) | Q(userprofile=profile))

        # Order by UserProfile.Meta.ordering
        memberships = memberships.order_by('userprofile')

        # Find the most common skills of the group members.
        # Order by popularity in the group.
        shared_skill_ids = (group.members.filter(groupmembership__status=GroupMembership.MEMBER)
                            .values_list('skills', flat=True))

        count_skills = defaultdict(int)
        for skill_id in shared_skill_ids:
            count_skills[skill_id] += 1
        common_skills_ids = [k for k, v in sorted(count_skills.items(),
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

    extra_data = dict(people=people,
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


def remove_member(request, url, user_pk):
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
        group.remove_member(profile_to_remove,
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
        if membership.status == GroupMembership.MEMBER:
            messages.error(request, _('This user is already a member of this group.'))
        else:
            status = GroupMembership.MEMBER
            if group.terms:
                status = GroupMembership.PENDING_TERMS
            group.add_member(profile, status=status)
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

    membership_form = TermsReviewForm(request.POST or None)
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
    elif group.accepting_new_members == 'no':
        messages.error(request, _('This group is not accepting requests to join.'))
    else:
        if group.accepting_new_members == 'yes':
            status = GroupMembership.MEMBER
            messages.info(request, _('You have been added to this group.'))
            if group.terms:
                status = GroupMembership.PENDING_TERMS
        elif group.accepting_new_members == 'by_request':
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
def group_add_edit(request, url=None):
    """
    Add or edit a group.  (If a url is passed in, we're editing.)
    """

    profile = request.user.userprofile
    is_manager = request.user.userprofile.is_manager

    if url:
        # Get the group to edit
        group = get_object_or_404(Group, url=url)
        # Only a group curator or an admin is allowed to edit a group
        is_curator = profile in group.curators.all()
        if not (is_curator or is_manager):
            messages.error(request, _('You must be a curator or an admin to edit a group'))
            return redirect(reverse('groups:show_group', args=[group.url]))
    else:
        group = Group()

    form_class = SuperuserGroupForm if is_manager else GroupForm

    curators_ids = [profile.id]
    if url:
        curators_ids += group.curators.all().values_list('id', flat=True)
    form = form_class(request.POST or None, instance=group,
                      initial={'curators': curators_ids})

    if form.is_valid():
        group = form.save()

        return redirect(reverse('groups:show_group', args=[group.url]))

    context = {
        'form': form,
        'creating': url is None,
        'group': group if url else None
    }
    return render(request, 'groups/add_edit.html', context)
