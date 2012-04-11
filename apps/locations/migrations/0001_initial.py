# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding model 'Country'
        db.create_table('locations_country', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('code', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('poly', self.gf('django.contrib.gis.db.models.fields.PolygonField')(null=True, spatial_index=False)),
        ))
        db.send_create_signal('locations', ['Country'])

        # Adding model 'Address'
        db.create_table('locations_address', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('street', self.gf('django.db.models.fields.CharField')(max_length=200, null=True)),
            ('city', self.gf('django.db.models.fields.CharField')(max_length=150, null=True)),
            ('province', self.gf('django.db.models.fields.CharField')(max_length=200, null=True)),
            ('postal_code', self.gf('django.db.models.fields.CharField')(max_length=50, null=True)),
            ('country', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['locations.Country'], null=True)),
            ('point', self.gf('django.contrib.gis.db.models.fields.PointField')(null=True, spatial_index=False)),
        ))
        db.send_create_signal('locations', ['Address'])

        from locations.models import COUNTRIES
        if not db.dry_run:
            for c in COUNTRIES.keys():
                orm.Country.objects.create(code=c)


    def backwards(self, orm):

        # Deleting model 'Country'
        db.delete_table('locations_country')

        # Deleting model 'Address'
        db.delete_table('locations_address')


    models = {
        'locations.address': {
            'Meta': {'object_name': 'Address'},
            'city': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True'}),
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['locations.Country']", 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'point': ('django.contrib.gis.db.models.fields.PointField', [], {'null': 'True', 'spatial_index': 'False'}),
            'postal_code': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True'}),
            'province': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'street': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'})
        },
        'locations.country': {
            'Meta': {'object_name': 'Country'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'poly': ('django.contrib.gis.db.models.fields.PolygonField', [], {'null': 'True', 'spatial_index': 'False'})
        }
    }

    complete_apps = ['locations']
