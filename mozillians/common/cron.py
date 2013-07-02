import os
import sys
from collections import defaultdict

import cronjobs

from django.conf import settings
from django.db import models
from django.db.models.loading import cache


@cronjobs.register
def find_orphaned_files(path=''):
    """Prints a list of all files in the path that are not referenced
    in the database by all apps.

    """
    if not getattr(settings, 'MEDIA_ROOT', None):
        sys.stdout.write('MEDIA_ROOT is not set, nothing to do')
        return

    # Get a list of all files under MEDIA_ROOT.
    media = set()
    for root, dirs, files in os.walk(os.path.join(settings.MEDIA_ROOT, path)):
        for f in files:
            media.add(os.path.abspath(os.path.join(root, f)))

    # Get list of all fields (value) for each model (key)
    # that is a FileField or subclass of a FileField.
    model_dict = defaultdict(list)
    for app in cache.get_apps():
        model_list = cache.get_models(app)
        for model in model_list:
            for field in model._meta.fields:
                if issubclass(field.__class__, models.FileField):
                    model_dict[model].append(field)

    # Get a list of all files referenced in the database.
    referenced = set()
    for model in model_dict.iterkeys():
        all = model.objects.all().iterator()
        for object in all:
            for field in model_dict[model]:
                f = getattr(object, field.name)
                if f:
                    referenced.add(os.path.abspath(f.path))

    # Print each file that is not referenced in the database.
    for f in sorted(media - referenced):
        sys.stdout.write(f)
        sys.stdout.write('\n')
