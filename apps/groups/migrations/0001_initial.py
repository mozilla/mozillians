# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Group'
        db.create_table('group', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50, db_index=True)),
            ('url', self.gf('django.db.models.fields.SlugField')(max_length=50, db_index=True)),
            ('auto_complete', self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True)),
            ('always_auto_complete', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('system', self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True)),
        ))
        db.send_create_signal('groups', ['Group'])


    def backwards(self, orm):
        
        # Deleting model 'Group'
        db.delete_table('group')


    models = {
        'groups.group': {
            'Meta': {'object_name': 'Group', 'db_table': "'group'"},
            'always_auto_complete': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'auto_complete': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'system': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'url': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'})
        }
    }

    complete_apps = ['groups']
