# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        # This was just a reaname of the model field, the db field stays the
        # same
        pass

    def backwards(self, orm):
        # This was just a reaname of the model field, the db field stays the
        # same.

        pass

    models = {
        'phonebook.invite': {
            'Meta': {'object_name': 'Invite', 'db_table': "'invite'"},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '32'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'inviter_old': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '32', 'db_column': "'inviter'"}),
            'recipient': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'redeemed': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'redeemer_old': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '32', 'db_column': "'redeemer'"})
        }
    }

    complete_apps = ['phonebook']
