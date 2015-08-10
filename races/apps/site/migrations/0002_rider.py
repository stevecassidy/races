# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('site', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Rider',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('licenceno', models.CharField(max_length=20, verbose_name=b'Licence Number')),
                ('gender', models.CharField(max_length=2, verbose_name=b'Gender', choices=[(b'M', b'M'), (b'F', b'F')])),
                ('club', models.ForeignKey(to='site.Club')),
                ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
