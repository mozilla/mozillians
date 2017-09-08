# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0019_userprofile_auth0_user_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='IdpProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.CharField(default=b'passwordless', max_length=50, choices=[(b'github', b'Github Provider'), (b'ldap', b'LDAP Provider'), (b'passwordless', b'Passwordless Provider'), (b'google', b'Google Provider')])),
                ('auth0_user_id', models.CharField(default=b'', max_length=1024, blank=True)),
            ],
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='auth0_user_id',
        ),
        migrations.AddField(
            model_name='idpprofile',
            name='profile',
            field=models.ForeignKey(related_name='idp_profiles', to='users.UserProfile'),
        ),
    ]
