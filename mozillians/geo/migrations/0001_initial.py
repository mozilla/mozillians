# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='City',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text=b'name field from Mapbox', max_length=120)),
                ('mapbox_id', models.CharField(help_text=b"'id' field from Mapbox", unique=True, max_length=40)),
                ('lat', models.FloatField()),
                ('lng', models.FloatField()),
            ],
            options={
                'verbose_name_plural': 'Cities',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Country',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text=b'name field from Mapbox', unique=True, max_length=120)),
                ('code', models.CharField(help_text=b'lowercased 2-letter code from Mozilla product data', max_length=2)),
                ('mapbox_id', models.CharField(help_text=b"'id' field from Mapbox", unique=True, max_length=40)),
            ],
            options={
                'verbose_name_plural': 'Countries',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Region',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text=b'name field from Mapbox', max_length=120)),
                ('mapbox_id', models.CharField(help_text=b"'id' field from Mapbox", unique=True, max_length=40)),
                ('country', models.ForeignKey(to='geo.Country')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='region',
            unique_together=set([('name', 'country')]),
        ),
        migrations.AddField(
            model_name='city',
            name='country',
            field=models.ForeignKey(to='geo.Country'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='city',
            name='region',
            field=models.ForeignKey(blank=True, to='geo.Region', null=True),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='city',
            unique_together=set([('name', 'region', 'country')]),
        ),
    ]
