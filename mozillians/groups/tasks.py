from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db.models import Count, Max
from django.db.models.loading import get_model
from django.template import Context
from django.template.loader import get_template, render_to_string

import tower
from celery.task import task
from tower import ugettext as _


@task(ignore_result=True)
def remove_empty_groups():
    """Remove empty groups."""
    Group = get_model('groups', 'Group')
    Skill = get_model('groups', 'Skill')

    for model in [Group, Skill]:
        (model.objects
         .annotate(mcount=Count('members')).filter(mcount=0).delete())


# TODO: Schedule this task nightly

@task(ignore_result=True)
def send_pending_membership_emails():
    """
    For each curated group that has pending memberships that the curator has not yet been
    emailed about, send the curator an email with the count of all pending memberships
    and a link to view and manage the requests.
    """
    Group = get_model('groups', 'Group')
    GroupMembership = get_model('groups', 'GroupMembership')

    # Curated groups that have pending membership requests
    groups = Group.objects.exclude(curator__isnull=True)
    groups = groups.filter(groupmembership__status=GroupMembership.PENDING)

    for group in groups:
        # what's the max pk of pending memberships?
        pending_memberships = GroupMembership.objects.filter(group=group,
                                                             status=GroupMembership.PENDING)
        max_pk = pending_memberships.aggregate(max_pk=Max('pk'))['max_pk']
        # Only send reminder if there are newer requests than we'd previously reminded about
        if max_pk > group.max_reminder:
            # TODO: Switch locale to curator's preferred language so translation will occur
            # Using English for now
            tower.activate('en-us')

            count = pending_memberships.count()
            subject = _('%d outstanding requests to join Mozillians group "%s"') % (
                count, group.name)
            body = render_to_string('groups/email/memberships_pending.txt', {
                'group': group,
                'count': count,
            })

            send_mail(subject, body, settings.FROM_NOREPLY,
                      [group.curator.user.email], fail_silently=False)

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
    Group = get_model('groups', 'Group')
    GroupMembership = get_model('groups', 'GroupMembership')

    group = Group.objects.get(pk=group_pk)
    user = User.objects.get(pk=user_pk)

    # TODO: Switch locale to user's preferred language so translation will occur
    # Using English for now
    tower.activate('en-us')

    if old_status == GroupMembership.PENDING:
        if new_status == GroupMembership.MEMBER:
            subject = _('Accepted to Mozillians group "%s"') % group.name
            template_name = 'groups/email/accepted.txt'
        elif new_status is None:
            subject = _('Not accepted to Mozillians group "%s"') % group.name
            template_name = 'groups/email/rejected.txt'
        else:
            # Odd things happen in some of our tests. Don't worry about it.
            raise ValueError("BAD ARGS TO email_membership_change")
    else:
        # Odd things happen in some of our tests. Don't worry about it.
        raise ValueError("BAD ARGS TO email_membership_change")

    context = {
        'group': group,
        'user': user,
    }
    template = get_template(template_name)
    body = template.render(Context(context))
    send_mail(subject, body, settings.FROM_NOREPLY,
              [user.email], fail_silently=False)
