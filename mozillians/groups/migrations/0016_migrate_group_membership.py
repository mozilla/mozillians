# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        # Note: Don't use "from appname.models import ModelName".
        # Use orm.ModelName to refer to models in this application,
        # and orm['appname.ModelName'] for models in other applications.
        for userprofile in orm['users.UserProfile'].objects.all():
            for grp in userprofile.groups.all():
                orm.GroupMembership.objects.create(
                    user=userprofile,
                    group=grp,
                    status='member')

    def backwards(self, orm):
        "Write your backwards methods here."
        for membership in orm.GroupMembership.objects.filter(status='member'):
            membership.user.groups.add(membership.group)

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
            'Meta': {'ordering': "['name']", 'object_name': 'Group'},
            'accepting_new_members': ('django.db.models.fields.CharField', [], {'default': "'by_request'", 'max_length': '10'}),
            'curator': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'groups_curated'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['users.UserProfile']"}),
            'description': ('django.db.models.fields.TextField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'functional_area': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'irc_channel': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '63', 'blank': 'True'}),
            'members_can_leave': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'url': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'blank': 'True'}),
            'visible': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'website': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'wiki': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200', 'blank': 'True'})
        },
        'groups.groupalias': {
            'Meta': {'object_name': 'GroupAlias'},
            'alias': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'aliases'", 'to': "orm['groups.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'url': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': "'name'", 'unique_with': '()', 'blank': 'True'})
        },
        'groups.groupmembership': {
            'Meta': {'unique_together': "(('user', 'group'),)", 'object_name': 'GroupMembership'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['groups.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['users.UserProfile']"})
        },
        'groups.language': {
            'Meta': {'ordering': "['name']", 'object_name': 'Language'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'url': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'blank': 'True'})
        },
        'groups.languagealias': {
            'Meta': {'object_name': 'LanguageAlias'},
            'alias': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'aliases'", 'to': "orm['groups.Language']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'url': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': "'name'", 'unique_with': '()', 'blank': 'True'})
        },
        'groups.skill': {
            'Meta': {'ordering': "['name']", 'object_name': 'Skill'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'url': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'blank': 'True'})
        },
        'groups.skillalias': {
            'Meta': {'object_name': 'SkillAlias'},
            'alias': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'aliases'", 'to': "orm['groups.Skill']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'url': ('autoslug.fields.AutoSlugField', [], {'unique': 'True', 'max_length': '50', 'populate_from': "'name'", 'unique_with': '()', 'blank': 'True'})
        },
        'users.userprofile': {
            'Meta': {'ordering': "['full_name']", 'object_name': 'UserProfile', 'db_table': "'profile'"},
            'allows_community_sites': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'allows_mozilla_sites': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'basket_token': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '1024', 'blank': 'True'}),
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'city': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'country': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50'}),
            'date_mozillian': ('django.db.models.fields.DateField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'date_vouched': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'full_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'members'", 'blank': 'True', 'to': "orm['groups.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ircname': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '63', 'blank': 'True'}),
            'is_vouched': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'languages': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'members'", 'blank': 'True', 'to': "orm['groups.Language']"}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now': 'True', 'blank': 'True'}),
            'photo': ('sorl.thumbnail.fields.ImageField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'privacy_bio': ('mozillians.users.models.PrivacyField', [], {'default': '3'}),
            'privacy_city': ('mozillians.users.models.PrivacyField', [], {'default': '3'}),
            'privacy_country': ('mozillians.users.models.PrivacyField', [], {'default': '3'}),
            'privacy_date_mozillian': ('mozillians.users.models.PrivacyField', [], {'default': '3'}),
            'privacy_email': ('mozillians.users.models.PrivacyField', [], {'default': '3'}),
            'privacy_full_name': ('mozillians.users.models.PrivacyField', [], {'default': '3'}),
            'privacy_groups': ('mozillians.users.models.PrivacyField', [], {'default': '3'}),
            'privacy_ircname': ('mozillians.users.models.PrivacyField', [], {'default': '3'}),
            'privacy_languages': ('mozillians.users.models.PrivacyField', [], {'default': '3'}),
            'privacy_photo': ('mozillians.users.models.PrivacyField', [], {'default': '3'}),
            'privacy_region': ('mozillians.users.models.PrivacyField', [], {'default': '3'}),
            'privacy_skills': ('mozillians.users.models.PrivacyField', [], {'default': '3'}),
            'privacy_timezone': ('mozillians.users.models.PrivacyField', [], {'default': '3'}),
            'privacy_title': ('mozillians.users.models.PrivacyField', [], {'default': '3'}),
            'privacy_tshirt': ('mozillians.users.models.PrivacyField', [], {'default': '1'}),
            'privacy_vouched_by': ('mozillians.users.models.PrivacyField', [], {'default': '3'}),
            'region': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'skills': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'members'", 'blank': 'True', 'to': "orm['groups.Skill']"}),
            'timezone': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '70', 'blank': 'True'}),
            'tshirt': ('django.db.models.fields.IntegerField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'}),
            'vouched_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'vouchees'", 'on_delete': 'models.SET_NULL', 'default': 'None', 'to': "orm['users.UserProfile']", 'blank': 'True', 'null': 'True'})
        }
    }

    complete_apps = ['groups']
    symmetrical = True
