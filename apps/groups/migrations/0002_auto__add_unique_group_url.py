# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

from groups.models import Group
from users.models import UserProfile

class Migration(SchemaMigration):

    def forwards(self, orm):
        if not db.dry_run:
            all_profiles = UserProfile.objects.all()
            for group in orm.Group.objects.extra(where=[('`url` IN ( '
                    'SELECT `url` FROM `group` GROUP BY `url` HAVING ('
                    'COUNT(`url`) > 1))')]):
                groups = orm.Group.objects.filter(url=group.url)
                group_ids = [g.id for g in groups]

                # South's access to ORM models is spotty and I'd rather this
                # be slow/inefficient than non-abstracted. I'm aware this could
                # be _greatly_ optimized, but I don't care: it only runs once.
                profile_ids = [p.id for p in all_profiles
                                    if p.groups.filter(id__in=group_ids)]

                # We're going to use the "first" group with a similar URL, so
                # make sure that all users who had any "related-by-URL" groups
                # now belong to this group.
                for p in UserProfile.objects.filter(id__in=profile_ids):
                    p.groups.add(Group.objects.get(id=group_ids[0]))

                # Cascading delete removes group membership in
                # UserProfile objects.
                for g in Group.objects.filter(id__in=group_ids[1:]):
                    g.delete()

        # Adding unique constraint on 'Group', fields ['url']
        db.create_unique('group', ['url'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Group', fields ['url']
        db.delete_unique('group', ['url'])


    models = {
        'groups.group': {
            'Meta': {'object_name': 'Group', 'db_table': "'group'"},
            'always_auto_complete': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'auto_complete': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'system': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'url': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        }
    }

    complete_apps = ['groups']
