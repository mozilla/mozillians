from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db.models import Count, Max
from django.template.loader import get_template, render_to_string
from django.utils.timezone import now
from django.utils.translation import activate, ungettext
from django.utils.translation import ugettext as _

from celery.task import periodic_task, task
from waffle import switch_is_active

from mozillians.common.templatetags.helpers import get_object_or_none


DAYS_BEFORE_INVALIDATION = 2 * 7  # 14 days


@task(ignore_result=True)
def remove_empty_groups():
    """Remove empty groups."""

    from mozillians.groups.models import Group, Skill

    for model in [Group, Skill]:
        model.objects.annotate(mcount=Count('members')).filter(mcount=0).delete()


# TODO: Schedule this task nightly

@task(ignore_result=True)
def send_pending_membership_emails():
    """
    For each curated group that has pending memberships that the curators have
    not yet been emailed about, send to all the curators an email with the count
    of all pending memberships and a link to view and manage the requests.
    """

    from mozillians.groups.models import Group, GroupMembership

    # Curated groups that have pending membership requests
    groups = Group.objects.exclude(curators__isnull=True)
    groups = groups.filter(groupmembership__status=GroupMembership.PENDING).distinct()

    for group in groups:
        # what's the max pk of pending memberships?
        pending_memberships = group.groupmembership_set.filter(status=GroupMembership.PENDING)
        max_pk = pending_memberships.aggregate(max_pk=Max('pk'))['max_pk']
        # Only send reminder if there are newer requests than we'd previously reminded about
        if max_pk > group.max_reminder:
            # TODO: Switch locale to curator's preferred language so translation will occur
            # Using English for now
            activate('en-us')

            count = pending_memberships.count()
            subject = ungettext(
                '%(count)d outstanding request to join Mozillians group "%(name)s"',
                '%(count)d outstanding requests to join Mozillians group "%(name)s"',
                count
            ) % {
                'count': count,
                'name': group.name
            }
            body = render_to_string('groups/email/memberships_pending.txt', {
                'group': group,
                'count': count,
            })

            send_mail(subject, body, settings.FROM_NOREPLY,
                      [profile.user.email for profile in group.curators.all()],
                      fail_silently=False)

            group.max_reminder = max_pk
            group.save()


@task(ignore_result=True)
def email_membership_change(group_pk, user_pk, old_status, new_status):
    """
    Email user that their group membership status has changed.

    old_status and new_status can either be a valid value for GroupMembership.status,
    or None if we're going from or to a state where there is no GroupMembership
    record (e.g. if they're being removed from a group).

    This is queued from Group.add_member() and Group.remove_member().
    """

    from mozillians.groups.models import Group, GroupMembership

    group = Group.objects.get(pk=group_pk)
    user = User.objects.get(pk=user_pk)

    # TODO: Switch locale to user's preferred language so translation will occur
    # Using English for now
    activate('en-us')

    if old_status in [GroupMembership.PENDING, GroupMembership.PENDING_TERMS]:
        if new_status == GroupMembership.MEMBER:
            subject = _('Accepted to Mozillians group "%s"') % group.name
            template_name = 'groups/email/accepted.txt'
        elif new_status is None:
            subject = _('Not accepted to Mozillians group "%s"') % group.name
            template_name = 'groups/email/rejected.txt'
        else:
            # Odd things happen in some of our tests. Don't worry about it.
            raise ValueError('BAD ARGS TO email_membership_change')
    else:
        if new_status in [GroupMembership.PENDING_TERMS, GroupMembership.PENDING]:
            subject = _('Status changed for Mozillians group "%s"') % group.name
            template_name = 'groups/email/membership_status_changed.txt'
        else:
            # The user is a member that was removed from the group.
            subject = _('Removed from Mozillians group "%s"') % group.name
            template_name = 'groups/email/member_removed.txt'

    context = {
        'group': group,
        'user': user,
    }
    template = get_template(template_name)
    body = template.render(context)
    send_mail(subject, body, settings.FROM_NOREPLY, [user.email], fail_silently=False)


@periodic_task(run_every=timedelta(hours=24))
def invalidate_group_membership():
    """
    For groups with defined `invalidation_days` we need to invalidate
    user membership after timedelta.
    """
    from mozillians.groups.models import Group, GroupMembership

    groups = Group.objects.filter(invalidation_days__isnull=False)

    for group in groups:
        curator_ids = group.curators.all().values_list('id', flat=True)
        last_update = now() - timedelta(days=group.invalidation_days)
        memberships = (group.groupmembership_set.filter(updated_on__lte=last_update)
                                                .exclude(userprofile__id__in=curator_ids))

        for member in memberships:
            status = None
            if group.accepting_new_members != Group.OPEN:
                status = GroupMembership.PENDING
            group.remove_member(member.userprofile, status=status)


@periodic_task(run_every=timedelta(hours=24))
def notify_membership_renewal():
    """
    For groups with defined `invalidation_days` we need to notify users
    2 weeks prior invalidation that the membership is expiring.
    """

    from mozillians.groups.models import Group, GroupMembership, Invite

    groups = (Group.objects.filter(invalidation_days__isnull=False,
                                   invalidation_days__gte=DAYS_BEFORE_INVALIDATION)
                           .exclude(accepting_new_members=Group.OPEN).distinct())

    for group in groups:
        curator_ids = group.curators.all().values_list('id', flat=True)
        memberships = (group.groupmembership_set.filter(status=GroupMembership.MEMBER)
                       .exclude(userprofile__id__in=curator_ids))

        # Filter memberships to be notified
        # Switch is being used only for testing mail notifications
        # It disables membership filtering based on date
        if not switch_is_active('test_membership_renewal_notification'):
            last_update_days = group.invalidation_days - DAYS_BEFORE_INVALIDATION
            last_update = now() - timedelta(days=last_update_days)

            query_start = datetime.combine(last_update.date(), datetime.min.time())
            query_end = datetime.combine(last_update.date(), datetime.max.time())

            query = {
                'updated_on__range': [query_start, query_end],
                'needs_renewal': False,
            }
            memberships = memberships.filter(**query)

        member_template = get_template('groups/email/notify_member_renewal.txt')
        curator_template = get_template('groups/email/notify_curator_renewal.txt')

        for membership in memberships:
            ctx = {
                'member_full_name': membership.userprofile.full_name,
                'group_name': membership.group.name,
                'group_url': membership.group.get_absolute_url(),
                'member_profile_url': membership.userprofile.get_absolute_url(),
                'inviter': None
            }

            invite = get_object_or_none(Invite, group=group, redeemer=membership.userprofile)
            if invite:
                ctx['inviter'] = invite.inviter

            subject_msg = unicode('[Mozillians] Your membership to Mozilla group "{0}" '
                                  'is about to expire')
            subject = _(subject_msg.format(membership.group.name))
            message = member_template.render(ctx)
            send_mail(subject, message, settings.FROM_NOREPLY, [membership.userprofile.email])

            subject_msg = unicode('[Mozillians][{0}] Membership of "{1}" is about to expire')
            format_args = [membership.group.name, membership.userprofile.full_name]
            subject = _(subject_msg.format(*format_args))

            # In case the membership was created after an invitation we notify inviters only
            # Else we fallback to all group curators
            curators = group.curators.all()
            inviter = ctx['inviter']
            if inviter and curators.filter(pk=inviter.id).exists():
                curators = [inviter]

            for curator in curators:
                ctx['curator_full_name'] = curator.full_name
                message = curator_template.render(ctx)
                send_mail(subject, message, settings.FROM_NOREPLY, [curator.email])

        # Mark these memberships ready for an early renewal
        memberships.update(needs_renewal=True)


@task(ignore_result=True)
def notify_redeemer_invitation(pk, custom_text=''):

    from mozillians.groups.models import Invite

    invite = Invite.objects.get(pk=pk)
    subject_msg = unicode('[Mozillians] You have been invited to join group "{0}"')
    subject = _(subject_msg.format(invite.group.name))
    template = get_template('groups/email/invite_email.txt')
    ctx = {
        'inviter_full_name': invite.inviter.full_name,
        'redeemer_full_name': invite.redeemer.full_name,
        'group_name': invite.group.name,
        'group_url': invite.group.get_absolute_url(),
        'custom_text': custom_text
    }
    message = template.render(ctx)
    send_mail(subject, message, settings.FROM_NOREPLY, [invite.redeemer.email])


@task(ignore_result=True)
def notify_curators_invitation_accepted(pk):

    from mozillians.groups.models import Invite

    invite = Invite.objects.get(pk=pk)
    subject_msg = unicode('[Mozillians] {0} has accepted your invitation to join group "{1}"')
    subject = _(subject_msg.format(invite.redeemer.full_name, invite.group.name))
    template = get_template('groups/email/invite_accepted_email.txt')
    ctx = {
        'inviter_full_name': invite.inviter.full_name,
        'redeemer_full_name': invite.redeemer.full_name,
        'group_name': invite.group.name,
        'group_url': invite.group.get_absolute_url()
    }
    message = template.render(ctx)
    send_mail(subject, message, settings.FROM_NOREPLY, [invite.inviter.email])


@task(ignore_result=True)
def notify_curators_invitation_rejected(redeemer_pk, inviter_pk, group_pk):

    from mozillians.groups.models import Group
    from mozillians.users.models import UserProfile

    inviter = UserProfile.objects.get(pk=inviter_pk)
    redeemer = UserProfile.objects.get(pk=redeemer_pk)
    group = Group.objects.get(pk=group_pk)

    subject_msg = unicode('[Mozillians] {0} has rejected your invitation to join group "{1}"')
    subject = _(subject_msg.format(redeemer.full_name, group.name))
    template = get_template('groups/email/invite_rejected_email.txt')
    ctx = {
        'redeemer_full_name': redeemer.full_name,
        'inviter_full_name': inviter.full_name,
        'group_name': group.name
    }
    message = template.render(ctx)
    send_mail(subject, message, settings.FROM_NOREPLY, [inviter.email])


@task(ignore_result=True)
def notify_redeemer_invitation_invalid(redeemer_pk, group_pk):

    from mozillians.groups.models import Group
    from mozillians.users.models import UserProfile

    group = Group.objects.get(pk=group_pk)
    redeemer = UserProfile.objects.get(pk=redeemer_pk)
    subject_msg = '[Mozillians] Invitation to group "{0}" is no longer valid'
    subject = _(subject_msg.format(group.name))
    template = get_template('groups/email/invite_invalid_email.txt')
    ctx = {
        'group_name': group.name,
        'redeemer_full_name': redeemer.full_name
    }
    message = template.render(ctx)
    send_mail(subject, message, settings.FROM_NOREPLY, [redeemer.email])
