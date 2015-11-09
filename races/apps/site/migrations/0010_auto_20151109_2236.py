# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('site', '0009_clubgrade'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pointscore',
            name='races',
            field=models.ManyToManyField(to='site.Race', blank=True),
        ),
    ]
