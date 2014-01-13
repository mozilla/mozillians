import json

from django.conf import settings
from django.contrib import messages
from django.core.paginator import EmptyPage, Paginator, PageNotAnInteger
from django.db.models import Count
from django.http import HttpResponse, HttpResponseBadRequest, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_control, never_cache
from django.views.decorators.http import require_POST

from funfactory.urlresolvers import reverse
from mozillians.users.models import UserProfile
from tower import ugettext as _

from mozillians.common.decorators import allow_unvouched
from mozillians.groups.forms import GroupForm, SortForm, SuperuserGroupForm
from mozillians.groups.models import Group, Skill, GroupAlias, GroupMembership


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
    """Lists all public groups (in use) on Mozillians."""
    # Omit functional areas, invisible groups, and groups with
    # no vouched members
    query = Group.get_non_functional_areas(members__is_vouched=True)
    template = 'groups/index_groups.html'
    return _list_groups(request, template, query)


def index_skills(request):
    """Lists all public skills (in use) on Mozillians."""
    query = (Skill.objects.filter(members__is_vouched=True)
             .annotate(num_members=Count('members')))
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

    Used for group/skill/language auto-completion.

    """
    term = request.GET.get('term', None)
    if request.is_ajax() and term:
        groups = searched_object.search(term).values_list('name', flat=True)
        return HttpResponse(json.dumps(list(groups)),
                            mimetype='application/json')

    return HttpResponseBadRequest()


@never_cache
def show(request, url, alias_model, template):
    """List all vouched users with this group."""
    group_alias = get_object_or_404(alias_model, url=url)
    if group_alias.alias.url != url:
        return redirect('groups:show_group', url=group_alias.alias.url)

    is_curator = False

    group = group_alias.alias
    profile = request.user.userprofile
    in_group = group.has_member(profile)

    if alias_model is GroupAlias:
        # Curator?
        is_curator = (group.curator == request.user.userprofile)
        if is_curator or request.user.is_superuser:
            # include all member statuses
            profiles = group.get_vouched_annotated_members()
        else:
            # only show full members, or this user
            profiles = group.get_vouched_annotated_members(statuses=[GroupMembership.MEMBER],
                                                           always_include=profile)
    else:
        profiles = group.members.vouched()

    page = request.GET.get('page', 1)
    paginator = Paginator(profiles, settings.ITEMS_PER_PAGE)

    try:
        people = paginator.page(page)
    except PageNotAnInteger:
        people = paginator.page(1)
    except EmptyPage:
        people = paginator.page(paginator.num_pages)

    show_pagination = paginator.count > settings.ITEMS_PER_PAGE

    data = dict(people=people,
                group=group,
                in_group=in_group,
                is_curator=is_curator,
                show_pagination=show_pagination,
                show_join_button=group.user_can_join(request.user.userprofile),
                show_leave_button=group.user_can_leave(request.user.userprofile),
                )

    if isinstance(group, Group):
        # Get the most globally popular skills that appear in the group
        # Sort them with most members first
        #
        skills = (Skill.objects
                  .filter(members__in=profiles)
                  .annotate(no_users=Count('members'))
                  .order_by('-no_users'))
        data.update(skills=skills)
        data.update(irc_channels=group.irc_channel.split(' '))
        data.update(members=paginator.count)

    return render(request, template, data)


def remove_member(request, group_pk, user_pk):
    group = get_object_or_404(Group, pk=group_pk)
    profile_to_remove = get_object_or_404(UserProfile, pk=user_pk)
    this_userprofile = request.user.userprofile
    is_curator = (group.curator == this_userprofile)
    is_superuser = request.user.is_superuser

    # TODO: this duplicates some of the logic in Group.user_can_leave(), but we
    # want to give the user a message that's specific to the reason they can't leave.
    # Can we make this DRYer?

    # You can remove yourself, if group allows it. Curator and superuser can remove anyone.
    if not (is_curator or is_superuser):
        if not group.members_can_leave:
            messages.error(request, _('This group does not allow members to remove themselves.'))
            return redirect('groups:show_group', url=group.url)
        if profile_to_remove != this_userprofile:
            raise Http404()

    # Curators cannot be removed, by anyone at all.
    if group.curator == profile_to_remove:
        messages.error(request, _('A curator cannot be removed from a group.'))
        return redirect('groups:show_group', url=group.url)

    if request.method == 'POST':
        group.remove_member(profile_to_remove,
                            send_email=(profile_to_remove != this_userprofile))
        if this_userprofile == profile_to_remove:
            messages.info(request, _('You have been removed from this group.'))
        else:
            messages.info(request, _('The group member has been removed.'))
        return redirect('groups:show_group', url=group.url)

    # Display confirmation page
    context = {
        'group': group,
        'profile': profile_to_remove
    }
    return render(request, 'groups/confirm_remove_member.html', context)


@require_POST
def confirm_member(request, group_pk, user_pk):
    """
    Add a member to a group who has requested membership.
    """
    group = get_object_or_404(Group, pk=group_pk)
    profile = get_object_or_404(UserProfile, pk=user_pk)
    is_curator = (group.curator == request.user.userprofile)
    if not (is_curator or request.user.is_superuser):
        raise Http404()
    try:
        membership = GroupMembership.objects.get(group=group, userprofile=profile)
    except GroupMembership.DoesNotExist:
        messages.error(request, _('This user has not requested membership in this group.'))
    else:
        if membership.status == GroupMembership.MEMBER:
            messages.error(request, _('This user is already a member of this group.'))
        else:
            group.add_member(profile)
            messages.info(request, _('This user has been added as a member of this group.'))
    return redirect('groups:show_group', url=group.url)


def edit(request, url, alias_model, template):
    return render(request, alias_model, template)


@require_POST
def join_group(request, group_pk):
    """User request to join group."""
    group = get_object_or_404(Group, pk=group_pk)
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
            group.add_member(profile_to_add)
            messages.info(request, _('You have been added to this group.'))
        elif group.accepting_new_members == 'by_request':
            group.add_member(profile_to_add, status=GroupMembership.PENDING)
            messages.info(request,
                          _('Your membership request is pending approval by the group curator.'))

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


def group_add_edit(request, url=None):
    """
    Add or edit a group.  (If a url is passed in, we're editing.)
    """

    profile = request.user.userprofile
    if url:
        # Get the group to edit
        group = get_object_or_404(Group, url=url)
        # Only a group curator or an admin is allowed to edit a group
        is_curator = profile == group.curator
        if not (is_curator or request.user.is_superuser):
            messages.error(request, _('You must be a curator or an admin to edit a group'))
            return redirect(reverse('groups:show_group', args=[group.url]))
    else:
        group = Group(curator=profile)

    form_class = SuperuserGroupForm if request.user.is_superuser else GroupForm

    form = form_class(request.POST or None, instance=group)
    if form.is_valid():
        group = form.save()
        # Ensure curator is in the group when it's created
        if profile == group.curator and not group.has_member(profile):
            group.add_member(profile)
        return redirect(reverse('groups:show_group', args=[group.url]))

    context = {
        'form': form,
        'creating': url is None,
        'group': group if url else None,
    }
    return render(request, 'groups/add_edit.html', context)
