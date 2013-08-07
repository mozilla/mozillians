# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'UserProfile.privacy_photo'
        db.add_column('profile', 'privacy_photo', self.gf('django.db.models.fields.PositiveIntegerField')(default=3), keep_default=False)

        # Adding field 'UserProfile.privacy_full_name'
        db.add_column('profile', 'privacy_full_name', self.gf('django.db.models.fields.PositiveIntegerField')(default=3), keep_default=False)

        # Adding field 'UserProfile.privacy_ircname'
        db.add_column('profile', 'privacy_ircname', self.gf('django.db.models.fields.PositiveIntegerField')(default=3), keep_default=False)

        # Adding field 'UserProfile.privacy_email'
        db.add_column('profile', 'privacy_email', self.gf('django.db.models.fields.PositiveIntegerField')(default=3), keep_default=False)

        # Adding field 'UserProfile.privacy_website'
        db.add_column('profile', 'privacy_website', self.gf('django.db.models.fields.PositiveIntegerField')(default=3), keep_default=False)

        # Adding field 'UserProfile.privacy_bio'
        db.add_column('profile', 'privacy_bio', self.gf('django.db.models.fields.PositiveIntegerField')(default=3), keep_default=False)

        # Adding field 'UserProfile.privacy_city'
        db.add_column('profile', 'privacy_city', self.gf('django.db.models.fields.PositiveIntegerField')(default=3), keep_default=False)

        # Adding field 'UserProfile.privacy_region'
        db.add_column('profile', 'privacy_region', self.gf('django.db.models.fields.PositiveIntegerField')(default=3), keep_default=False)

        # Adding field 'UserProfile.privacy_country'
        db.add_column('profile', 'privacy_country', self.gf('django.db.models.fields.PositiveIntegerField')(default=3), keep_default=False)

        # Adding field 'UserProfile.privacy_groups'
        db.add_column('profile', 'privacy_groups', self.gf('django.db.models.fields.PositiveIntegerField')(default=3), keep_default=False)

        # Adding field 'UserProfile.privacy_skills'
        db.add_column('profile', 'privacy_skills', self.gf('django.db.models.fields.PositiveIntegerField')(default=3), keep_default=False)

        # Adding field 'UserProfile.privacy_languages'
        db.add_column('profile', 'privacy_languages', self.gf('django.db.models.fields.PositiveIntegerField')(default=3), keep_default=False)

        # Adding field 'UserProfile.privacy_vouched_by'
        db.add_column('profile', 'privacy_vouched_by', self.gf('django.db.models.fields.PositiveIntegerField')(default=3), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'UserProfile.privacy_photo'
        db.delete_column('profile', 'privacy_photo')

        # Deleting field 'UserProfile.privacy_full_name'
        db.delete_column('profile', 'privacy_full_name')

        # Deleting field 'UserProfile.privacy_ircname'
        db.delete_column('profile', 'privacy_ircname')

        # Deleting field 'UserProfile.privacy_email'
        db.delete_column('profile', 'privacy_email')

        # Deleting field 'UserProfile.privacy_website'
        db.delete_column('profile', 'privacy_website')

        # Deleting field 'UserProfile.privacy_bio'
        db.delete_column('profile', 'privacy_bio')

        # Deleting field 'UserProfile.privacy_city'
        db.delete_column('profile', 'privacy_city')

        # Deleting field 'UserProfile.privacy_region'
        db.delete_column('profile', 'privacy_region')

        # Deleting field 'UserProfile.privacy_country'
        db.delete_column('profile', 'privacy_country')

        # Deleting field 'UserProfile.privacy_groups'
        db.delete_column('profile', 'privacy_groups')

        # Deleting field 'UserProfile.privacy_skills'
        db.delete_column('profile', 'privacy_skills')

        # Deleting field 'UserProfile.privacy_languages'
        db.delete_column('profile', 'privacy_languages')

        # Deleting field 'UserProfile.privacy_vouched_by'
        db.delete_column('profile', 'privacy_vouched_by')


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
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 3, 14, 4, 50, 26, 134351)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 3, 14, 4, 50, 26, 134291)'}),
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
            'url': ('autoslug.fields.AutoSlugField', [], {'unique_with': '()', 'max_length': '50', 'blank': 'True', 'unique': 'True', 'populate_from': "'name'", 'db_index': 'True'}),
            'website': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'wiki': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'})
        },
        'groups.language': {
            'Meta': {'object_name': 'Language'},
            'always_auto_complete': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'auto_complete': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'url': ('autoslug.fields.AutoSlugField', [], {'unique_with': '()', 'max_length': '50', 'blank': 'True', 'unique': 'True', 'populate_from': "'name'", 'db_index': 'True'})
        },
        'groups.skill': {
            'Meta': {'object_name': 'Skill'},
            'always_auto_complete': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'auto_complete': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'url': ('autoslug.fields.AutoSlugField', [], {'unique_with': '()', 'max_length': '50', 'blank': 'True', 'unique': 'True', 'populate_from': "'name'", 'db_index': 'True'})
        },
        'users.usernameblacklist': {
            'Meta': {'ordering': "['value']", 'object_name': 'UsernameBlacklist'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_regex': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'value': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'users.userprofile': {
            'Meta': {'ordering': "['full_name']", 'object_name': 'UserProfile', 'db_table': "'profile'"},
            'allows_community_sites': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'allows_mozilla_sites': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'basket_token': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '1024', 'blank': 'True'}),
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'city': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'country': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50', 'blank': 'True'}),
            'full_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['groups.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ircname': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '63', 'blank': 'True'}),
            'is_vouched': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'languages': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['groups.Language']", 'symmetrical': 'False', 'blank': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now': 'True', 'blank': 'True'}),
            'photo': ('sorl.thumbnail.fields.ImageField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'privacy_bio': ('django.db.models.fields.PositiveIntegerField', [], {'default': '3'}),
            'privacy_city': ('django.db.models.fields.PositiveIntegerField', [], {'default': '3'}),
            'privacy_country': ('django.db.models.fields.PositiveIntegerField', [], {'default': '3'}),
            'privacy_email': ('django.db.models.fields.PositiveIntegerField', [], {'default': '3'}),
            'privacy_full_name': ('django.db.models.fields.PositiveIntegerField', [], {'default': '3'}),
            'privacy_groups': ('django.db.models.fields.PositiveIntegerField', [], {'default': '3'}),
            'privacy_ircname': ('django.db.models.fields.PositiveIntegerField', [], {'default': '3'}),
            'privacy_languages': ('django.db.models.fields.PositiveIntegerField', [], {'default': '3'}),
            'privacy_photo': ('django.db.models.fields.PositiveIntegerField', [], {'default': '3'}),
            'privacy_region': ('django.db.models.fields.PositiveIntegerField', [], {'default': '3'}),
            'privacy_skills': ('django.db.models.fields.PositiveIntegerField', [], {'default': '3'}),
            'privacy_vouched_by': ('django.db.models.fields.PositiveIntegerField', [], {'default': '3'}),
            'privacy_website': ('django.db.models.fields.PositiveIntegerField', [], {'default': '3'}),
            'region': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'skills': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['groups.Skill']", 'symmetrical': 'False', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'}),
            'vouched_by': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'vouchees'", 'null': 'True', 'blank': 'True', 'to': "orm['users.UserProfile']"}),
            'website': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['users']
