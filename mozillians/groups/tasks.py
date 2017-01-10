from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db.models import Count, Max
from django.template.loader import get_template, render_to_string
from django.utils.translation import activate, ungettext
from django.utils.translation import ugettext as _

from celery.task import periodic_task, task


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
        # Odd things happen in some of our tests. Don't worry about it.
        raise ValueError('BAD ARGS TO email_membership_change')

    context = {
        'group': group,
        'user': user,
    }
    template = get_template(template_name)
    body = template.render(context)
    send_mail(subject, body, settings.FROM_NOREPLY,
              [user.email], fail_silently=False)


@task(ignore_result=True)
def member_removed_email(group_pk, user_pk):
    """
    Email to member when he is removed from group
    """

    from mozillians.groups.models import Group

    group = Group.objects.get(pk=group_pk)
    user = User.objects.get(pk=user_pk)
    activate('en-us')
    template_name = 'groups/email/member_removed.txt'
    subject = _('Removed from Mozillians group "%s"') % group.name
    template = get_template(template_name)
    context = {
        'group': group,
        'user': user,
    }
    body = template.render(context)
    send_mail(subject, body, settings.FROM_NOREPLY,
              [user.email], fail_silently=False)


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
        memberships = (group.groupmembership_set.filter(status=GroupMembership.MEMBER)
                                                .exclude(userprofile__id__in=curator_ids))

        last_update = datetime.now() - timedelta(days=group.invalidation_days)
        memberships = memberships.filter(updated_on__lte=last_update)

        for membership in memberships:
            membership.status = GroupMembership.PENDING
            membership.save()


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
