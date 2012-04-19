# encoding: utf-8
from south.db import db
from south.v2 import SchemaMigration

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

        # Rename url to slug
        db.rename_column('group', 'url', 'slug')


    def backwards(self, orm):

        # Reverse renaming.
        db.rename_column('group', 'slug', 'url')

        # Removing unique constraint on 'Group', fields ['url']
        db.delete_unique('group', ['url'])


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'groups.group': {
            'Meta': {'object_name': 'Group', 'db_table': "'group'"},
            'always_auto_complete': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'auto_complete': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'irc_channel': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '63', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'steward': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['users.UserProfile']", 'null': 'True', 'blank': 'True'}),
            'system': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'url': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'website': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'wiki': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'})
        },
        'groups.skill': {
            'Meta': {'object_name': 'Skill'},
            'always_auto_complete': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'auto_complete': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile', 'db_table': "'profile'"},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['groups.Group']", 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ircname': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '63', 'blank': 'True'}),
            'is_vouched': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now': 'True', 'blank': 'True'}),
            'photo': ('sorl.thumbnail.fields.ImageField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'skills': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['groups.Skill']", 'symmetrical': 'False'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'}),
            'vouched_by': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['users.UserProfile']", 'null': 'True'}),
            'website': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['groups']
