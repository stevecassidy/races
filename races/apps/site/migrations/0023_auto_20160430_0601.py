# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-04-30 03:01
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('site', '0022_auto_20160430_0555'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rider',
            name='emergencyphone',
            field=models.CharField(default=b'', max_length=50, verbose_name=b'Emergency Contact Phone'),
        ),
    ]
