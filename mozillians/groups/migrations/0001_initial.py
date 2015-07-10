# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import autoslug.fields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=50, verbose_name='Name', db_index=True)),
                ('url', models.SlugField(blank=True)),
                ('description', models.TextField(default=b'', max_length=255, verbose_name='Description', blank=True)),
                ('irc_channel', models.CharField(default=b'', help_text='An IRC channel where this group is discussed (optional).', max_length=63, verbose_name='IRC Channel', blank=True)),
                ('website', models.URLField(default=b'', help_text='A URL of a web site with more information about this group (optional).', verbose_name='Website', blank=True)),
                ('wiki', models.URLField(default=b'', help_text='A URL of a wiki with more information about this group (optional).', verbose_name='Wiki', blank=True)),
                ('members_can_leave', models.BooleanField(default=True)),
                ('accepting_new_members', models.CharField(default=b'yes', max_length=10, verbose_name='Accepting new members', choices=[(b'yes', 'Yes'), (b'by_request', 'By request'), (b'no', 'No')])),
                ('new_member_criteria', models.TextField(default=b'', help_text='Specify the criteria you will use to decide whether or not you will accept a membership request.', max_length=255, verbose_name='New Member Criteria', blank=True)),
                ('functional_area', models.BooleanField(default=False)),
                ('visible', models.BooleanField(default=True, help_text='Whether group is shown on the UI (in group lists, search, etc). Mainly intended to keep system groups like "staff" from cluttering up the interface.')),
                ('max_reminder', models.IntegerField(default=0, help_text='The max PK of pending membership requests the last time we sent the curator a reminder')),
            ],
            options={
                'ordering': ['name'],
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GroupAlias',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=50)),
                ('url', autoslug.fields.AutoSlugField(unique=True, editable=False, blank=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GroupMembership',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.CharField(max_length=10, choices=[('member', 'Member'), ('pending', 'Pending')])),
                ('date_joined', models.DateTimeField(null=True, blank=True)),
                ('group', models.ForeignKey(to='groups.Group')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Skill',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=50, verbose_name='Name', db_index=True)),
                ('url', models.SlugField(blank=True)),
            ],
            options={
                'ordering': ['name'],
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SkillAlias',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=50)),
                ('url', autoslug.fields.AutoSlugField(unique=True, editable=False, blank=True)),
                ('alias', models.ForeignKey(related_name='aliases', to='groups.Skill')),
            ],
            options={
                'verbose_name_plural': 'skill aliases',
            },
            bases=(models.Model,),
        ),
    ]
