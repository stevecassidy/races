# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2017-08-09 11:37
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cabici', '0008_membership_date'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='membership',
            name='year',
        ),
    ]
