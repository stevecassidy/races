# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('site', '0005_auto_20150906_0720'),
    ]

    operations = [
        migrations.AddField(
            model_name='rider',
            name='official',
            field=models.BooleanField(default=False, verbose_name=b'Club Official'),
        ),
    ]
