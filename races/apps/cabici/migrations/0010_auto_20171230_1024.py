# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-12-30 08:24
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cabici', '0009_remove_membership_year'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='racestaff',
            unique_together=set([('rider', 'race', 'role')]),
        ),
    ]