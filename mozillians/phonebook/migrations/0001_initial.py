# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Invite'
        db.create_table('invite', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('inviter', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('recipient', self.gf('django.db.models.fields.EmailField')(max_length=75)),
            ('redeemer', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('code', self.gf('django.db.models.fields.CharField')(unique=True, max_length=32)),
            ('redeemed', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('phonebook', ['Invite'])


    def backwards(self, orm):
        
        # Deleting model 'Invite'
        db.delete_table('invite')


    models = {
        'phonebook.invite': {
            'Meta': {'object_name': 'Invite', 'db_table': "'invite'"},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '32'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'inviter': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'recipient': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'redeemed': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'redeemer': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        }
    }

    complete_apps = ['phonebook']
