# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('site', '0008_auto_20151107_0441'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClubGrade',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('grade', models.CharField(max_length=10, verbose_name=b'Grade')),
                ('club', models.ForeignKey(to='site.Club')),
                ('rider', models.ForeignKey(to='site.Rider')),
            ],
        ),
    ]
