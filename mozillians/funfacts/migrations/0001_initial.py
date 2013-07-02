# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'FunFact'
        db.create_table('funfacts_funfact', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('published', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('public_text', self.gf('django.db.models.fields.TextField')()),
            ('number', self.gf('django.db.models.fields.TextField')(max_length=1000)),
            ('divisor', self.gf('django.db.models.fields.TextField')(max_length=1000, null=True, blank=True)),
        ))
        db.send_create_signal('funfacts', ['FunFact'])


    def backwards(self, orm):
        
        # Deleting model 'FunFact'
        db.delete_table('funfacts_funfact')


    models = {
        'funfacts.funfact': {
            'Meta': {'ordering': "['created']", 'object_name': 'FunFact'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'divisor': ('django.db.models.fields.TextField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'number': ('django.db.models.fields.TextField', [], {'max_length': '1000'}),
            'public_text': ('django.db.models.fields.TextField', [], {}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['funfacts']
