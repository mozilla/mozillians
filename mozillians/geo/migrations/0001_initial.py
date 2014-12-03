# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Country'
        db.create_table('geo_country', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=120)),
            ('code', self.gf('django.db.models.fields.CharField')(unique=True, max_length=2)),
            ('mapbox_id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=40)),
        ))
        db.send_create_signal('geo', ['Country'])

        # Adding model 'Region'
        db.create_table('geo_region', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=120)),
            ('mapbox_id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=40)),
            ('country', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['geo.Country'])),
        ))
        db.send_create_signal('geo', ['Region'])

        # Adding model 'City'
        db.create_table('geo_city', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=120)),
            ('mapbox_id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=40)),
            ('region', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['geo.Region'], null=True, blank=True)),
            ('country', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['geo.Country'])),
            ('lat', self.gf('django.db.models.fields.FloatField')()),
            ('lng', self.gf('django.db.models.fields.FloatField')()),
            ('w', self.gf('django.db.models.fields.FloatField')(default=None, null=True, blank=True)),
            ('s', self.gf('django.db.models.fields.FloatField')(default=None, null=True, blank=True)),
            ('e', self.gf('django.db.models.fields.FloatField')(default=None, null=True, blank=True)),
            ('n', self.gf('django.db.models.fields.FloatField')(default=None, null=True, blank=True)),
        ))
        db.send_create_signal('geo', ['City'])

        # Adding model 'Geocoding'
        db.create_table('geo_geocoding', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('country', self.gf('django.db.models.fields.CharField')(default='', max_length=50)),
            ('region', self.gf('django.db.models.fields.CharField')(default='', max_length=255, blank=True)),
            ('city', self.gf('django.db.models.fields.CharField')(default='', max_length=255, blank=True)),
            ('geo_country', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['geo.Country'])),
            ('geo_region', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['geo.Region'], null=True, on_delete=models.SET_NULL, blank=True)),
            ('geo_city', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['geo.City'], null=True, on_delete=models.SET_NULL, blank=True)),
        ))
        db.send_create_signal('geo', ['Geocoding'])


    def backwards(self, orm):
        # Deleting model 'Country'
        db.delete_table('geo_country')

        # Deleting model 'Region'
        db.delete_table('geo_region')

        # Deleting model 'City'
        db.delete_table('geo_city')

        # Deleting model 'Geocoding'
        db.delete_table('geo_geocoding')


    models = {
        'geo.city': {
            'Meta': {'object_name': 'City'},
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['geo.Country']"}),
            'e': ('django.db.models.fields.FloatField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lat': ('django.db.models.fields.FloatField', [], {}),
            'lng': ('django.db.models.fields.FloatField', [], {}),
            'mapbox_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40'}),
            'n': ('django.db.models.fields.FloatField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '120'}),
            'region': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['geo.Region']", 'null': 'True', 'blank': 'True'}),
            's': ('django.db.models.fields.FloatField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'w': ('django.db.models.fields.FloatField', [], {'default': 'None', 'null': 'True', 'blank': 'True'})
        },
        'geo.country': {
            'Meta': {'object_name': 'Country'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '2'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mapbox_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '120'})
        },
        'geo.geocoding': {
            'Meta': {'object_name': 'Geocoding'},
            'city': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'country': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50'}),
            'geo_city': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['geo.City']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'geo_country': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['geo.Country']"}),
            'geo_region': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['geo.Region']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'region': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'})
        },
        'geo.region': {
            'Meta': {'object_name': 'Region'},
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['geo.Country']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mapbox_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '120'})
        }
    }

    complete_apps = ['geo']