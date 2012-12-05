import os
import random
from string import letters

from django import test
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files import File

from elasticutils.contrib.django import get_es


def user(**kwargs):
    profile_changes = {}
    if 'username' not in kwargs:
        kwargs['username'] = ''.join(
            random.choice(letters) for x in xrange(15))
    if 'email' not in kwargs:
        kwargs['email'] = ''.join(
            random.choice(letters) for x in xrange(15)) + '@example.com'
    if 'vouched' in kwargs:
        profile_changes['vouched'] = kwargs['vouched']
        del kwargs['vouched']
    if 'photo' in kwargs:
        profile_changes['photo'] = kwargs['photo']
        del kwargs['photo']
    if 'full_name' in kwargs:
        profile_changes['full_name'] = kwargs['full_name']
        del kwargs['full_name']

    user = User.objects.create(**kwargs)
    user.save()

    if profile_changes:
        profile = user.get_profile()
        profile.full_name = profile_changes.get(
            'full_name',
            ''.join(random.choice(letters) for x in xrange(15)))
        profile.is_vouched = profile_changes.get('vouched', False)
        if profile_changes.get('photo', False):
            with open(os.path.join(os.path.dirname(__file__),
                      'profile-photo.jpg')) as f:
                profile.photo = File(f)
                profile.save()
        profile.save()

    if not settings.ES_DISABLED:
        get_es().refresh(settings.ES_INDEXES['default'], timesleep=0)

    return user


def create_client(**kwargs):
    client = test.Client()
    u = user(**kwargs)
    client.login(email=u.email)
    return client
