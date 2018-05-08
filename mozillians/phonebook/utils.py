import boto3
import datetime
import json
import waffle

from anytree import Node
from anytree.exporter import DictExporter

from django.conf import settings

from mozillians.phonebook.models import Invite
from mozillians.users.models import IdpProfile


def redeem_invite(redeemer, code):
    if code:
        try:
            invite = Invite.objects.get(code=code, redeemed=None)
            voucher = invite.inviter
        except Invite.DoesNotExist:
            return
    else:
        # If there is no invite, lets get out of here.
        return

    redeemer.vouch(voucher, invite.reason)
    invite.redeemed = datetime.datetime.now()
    invite.redeemer = redeemer
    invite.send_thanks()
    invite.save()


def create_orgchart():
    """Generate orgchart dict from s3 json dump."""

    s3 = boto3.resource('s3')

    if waffle.switch_is_active('use_mock_hr'):
        # Do not import mock data in prod
        from mozillians.users.tests import MockOrgChart
        orgchart_json = MockOrgChart.generate_json()
    else:
        orgchart_object = s3.Object(settings.ORGCHART_BUCKET, settings.ORGCHART_KEY).get()
        orgchart_json = orgchart_object['Body'].read()

    data = json.loads(orgchart_json)

    entries = data['Report_Entry']
    graph = {
        'root': [],
    }

    # Create adjacency list
    for entry in entries:
        if 'WorkersManagersEmployeeID' not in entry:
            graph['root'].append(entry['EmployeeID'])
            continue

        if entry['WorkersManagersEmployeeID'] not in graph:
            graph[entry['WorkersManagersEmployeeID']] = [entry['EmployeeID']]
        else:
            graph[entry['WorkersManagersEmployeeID']].append(entry['EmployeeID'])

    # Create nodes dict
    nodes = {
        'root': Node(name='root', title='root')
    }

    for entry in entries:
        # Encode values to utf8
        first_name = entry['PreferredFirstName'].encode('utf8')
        last_name = entry['Preferred_Name_-_Last_Name'].encode('utf8')
        name = '{} {}'.format(first_name, last_name)
        title = entry['businessTitle'].encode('utf8')
        href = get_profile_link_by_email(entry['PrimaryWorkEmail']).encode('utf8')

        nodes[entry['EmployeeID']] = Node(name=name, title=title, href=href)

    # Create graph
    for key in graph:
        parent = nodes[key]
        for child in graph[key]:
            node = nodes[child]

            if node == parent:
                # Workaround for data incosistency
                node.parent = nodes['root']
                continue

            node.parent = parent

    exporter = DictExporter()
    return exporter.export(nodes['root'])


def get_profile_link_by_email(email):
    try:
        idp_profile = IdpProfile.objects.get(email=email)
    except (IdpProfile.DoesNotExist, IdpProfile.MultipleObjectsReturned):
        return "#"
    else:
        return idp_profile.profile.get_absolute_url()
