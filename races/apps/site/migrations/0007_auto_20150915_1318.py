# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('site', '0006_rider_official'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='raceresult',
            unique_together=set([('race', 'grade', 'number'), ('race', 'rider')]),
        ),
    ]
