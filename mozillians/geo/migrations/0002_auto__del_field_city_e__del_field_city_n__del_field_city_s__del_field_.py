# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'City.e'
        db.delete_column('geo_city', 'e')

        # Deleting field 'City.n'
        db.delete_column('geo_city', 'n')

        # Deleting field 'City.s'
        db.delete_column('geo_city', 's')

        # Deleting field 'City.w'
        db.delete_column('geo_city', 'w')

        # Adding unique constraint on 'City', fields ['country', 'region', 'name']
        db.create_unique('geo_city', ['country_id', 'region_id', 'name'])

        # Adding unique constraint on 'Region', fields ['country', 'name']
        db.create_unique('geo_region', ['country_id', 'name'])


    def backwards(self, orm):
        # Removing unique constraint on 'Region', fields ['country', 'name']
        db.delete_unique('geo_region', ['country_id', 'name'])

        # Removing unique constraint on 'City', fields ['country', 'region', 'name']
        db.delete_unique('geo_city', ['country_id', 'region_id', 'name'])

        # Adding field 'City.e'
        db.add_column('geo_city', 'e',
                      self.gf('django.db.models.fields.FloatField')(default=None, null=True, blank=True),
                      keep_default=False)

        # Adding field 'City.n'
        db.add_column('geo_city', 'n',
                      self.gf('django.db.models.fields.FloatField')(default=None, null=True, blank=True),
                      keep_default=False)

        # Adding field 'City.s'
        db.add_column('geo_city', 's',
                      self.gf('django.db.models.fields.FloatField')(default=None, null=True, blank=True),
                      keep_default=False)

        # Adding field 'City.w'
        db.add_column('geo_city', 'w',
                      self.gf('django.db.models.fields.FloatField')(default=None, null=True, blank=True),
                      keep_default=False)


    models = {
        'geo.city': {
            'Meta': {'unique_together': "(('name', 'region', 'country'),)", 'object_name': 'City'},
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['geo.Country']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lat': ('django.db.models.fields.FloatField', [], {}),
            'lng': ('django.db.models.fields.FloatField', [], {}),
            'mapbox_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '120'}),
            'region': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['geo.Region']", 'null': 'True', 'blank': 'True'})
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
            'Meta': {'unique_together': "(('name', 'country'),)", 'object_name': 'Region'},
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['geo.Country']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mapbox_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '120'})
        }
    }

    complete_apps = ['geo']