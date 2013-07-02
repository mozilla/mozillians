# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Announcement'
        db.create_table('announcements_announcement', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('text', self.gf('django.db.models.fields.TextField')(max_length=750)),
            ('image', self.gf('sorl.thumbnail.fields.ImageField')(default='', max_length=100, blank=True)),
            ('publish_from', self.gf('django.db.models.fields.DateTimeField')()),
            ('publish_until', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('announcements', ['Announcement'])


    def backwards(self, orm):
        
        # Deleting model 'Announcement'
        db.delete_table('announcements_announcement')


    models = {
        'announcements.announcement': {
            'Meta': {'ordering': "['-publish_from']", 'object_name': 'Announcement'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('sorl.thumbnail.fields.ImageField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'publish_from': ('django.db.models.fields.DateTimeField', [], {}),
            'publish_until': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {'max_length': '750'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['announcements']
