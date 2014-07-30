# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'Geocoding'
        db.delete_table(u'geo_geocoding')


    def backwards(self, orm):
        # Adding model 'Geocoding'
        db.create_table(u'geo_geocoding', (
            ('city', self.gf('django.db.models.fields.CharField')(default='', max_length=255, blank=True)),
            ('geo_country', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['geo.Country'])),
            ('country', self.gf('django.db.models.fields.CharField')(default='', max_length=50)),
            ('geo_city', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['geo.City'], null=True, on_delete=models.SET_NULL, blank=True)),
            ('region', self.gf('django.db.models.fields.CharField')(default='', max_length=255, blank=True)),
            ('geo_region', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['geo.Region'], null=True, on_delete=models.SET_NULL, blank=True)),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal(u'geo', ['Geocoding'])


    models = {
        u'geo.city': {
            'Meta': {'unique_together': "(('name', 'region', 'country'),)", 'object_name': 'City'},
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['geo.Country']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lat': ('django.db.models.fields.FloatField', [], {}),
            'lng': ('django.db.models.fields.FloatField', [], {}),
            'mapbox_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '120'}),
            'region': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['geo.Region']", 'null': 'True', 'blank': 'True'})
        },
        u'geo.country': {
            'Meta': {'object_name': 'Country'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mapbox_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '120'})
        },
        u'geo.region': {
            'Meta': {'unique_together': "(('name', 'country'),)", 'object_name': 'Region'},
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['geo.Country']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mapbox_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '120'})
        }
    }

    complete_apps = ['geo']