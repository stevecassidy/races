# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-07-19 12:38
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('site', '0024_auto_20160616_0137'),
    ]

    operations = [
        migrations.AlterField(
            model_name='racestaff',
            name='race',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='officials', to='site.Race'),
        ),
    ]
