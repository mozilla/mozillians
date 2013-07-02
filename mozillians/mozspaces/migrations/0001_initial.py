# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'MozSpace'
        db.create_table('mozspaces_mozspace', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('address', self.gf('django.db.models.fields.CharField')(max_length=300)),
            ('region', self.gf('django.db.models.fields.CharField')(default='', max_length=100, blank=True)),
            ('city', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('country', self.gf('django.db.models.fields.CharField')(max_length=5)),
            ('timezone', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('lon', self.gf('django.db.models.fields.FloatField')()),
            ('lat', self.gf('django.db.models.fields.FloatField')()),
            ('phone', self.gf('django.db.models.fields.CharField')(default='', max_length=100, blank=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(default='', max_length=75, blank=True)),
            ('coordinator', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('extra_text', self.gf('django.db.models.fields.TextField')(default='', blank=True)),
            ('cover_photo', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='featured_mozspace', null=True, to=orm['mozspaces.Photo'])),
        ))
        db.send_create_signal('mozspaces', ['MozSpace'])

        # Adding model 'Keyword'
        db.create_table('mozspaces_keyword', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('keyword', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50)),
            ('mozspace', self.gf('django.db.models.fields.related.ForeignKey')(related_name='keywords', to=orm['mozspaces.MozSpace'])),
        ))
        db.send_create_signal('mozspaces', ['Keyword'])

        # Adding model 'Photo'
        db.create_table('mozspaces_photo', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('photofile', self.gf('django.db.models.fields.files.ImageField')(max_length=100)),
            ('mozspace', self.gf('django.db.models.fields.related.ForeignKey')(related_name='photos', to=orm['mozspaces.MozSpace'])),
        ))
        db.send_create_signal('mozspaces', ['Photo'])


    def backwards(self, orm):
        
        # Deleting model 'MozSpace'
        db.delete_table('mozspaces_mozspace')

        # Deleting model 'Keyword'
        db.delete_table('mozspaces_keyword')

        # Deleting model 'Photo'
        db.delete_table('mozspaces_photo')


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
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 2, 11, 5, 41, 51, 842704)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 2, 11, 5, 41, 51, 842643)'}),
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
        'mozspaces.keyword': {
            'Meta': {'object_name': 'Keyword'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keyword': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'mozspace': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'keywords'", 'to': "orm['mozspaces.MozSpace']"})
        },
        'mozspaces.mozspace': {
            'Meta': {'object_name': 'MozSpace'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'coordinator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'country': ('django.db.models.fields.CharField', [], {'max_length': '5'}),
            'cover_photo': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'featured_mozspace'", 'null': 'True', 'to': "orm['mozspaces.Photo']"}),
            'email': ('django.db.models.fields.EmailField', [], {'default': "''", 'max_length': '75', 'blank': 'True'}),
            'extra_text': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lat': ('django.db.models.fields.FloatField', [], {}),
            'lon': ('django.db.models.fields.FloatField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'phone': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'region': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100', 'blank': 'True'}),
            'timezone': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'mozspaces.photo': {
            'Meta': {'object_name': 'Photo'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mozspace': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'photos'", 'to': "orm['mozspaces.MozSpace']"}),
            'photofile': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['mozspaces']
