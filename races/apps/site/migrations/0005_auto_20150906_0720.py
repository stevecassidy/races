# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('site', '0004_auto_20150906_0713'),
    ]

    operations = [
        migrations.AlterField(
            model_name='raceresult',
            name='place',
            field=models.IntegerField(help_text=b'Enter finishing position (eg. 1-5), leave blank for a result out of the placings.', null=True, verbose_name=b'Place', blank=True),
        ),
    ]
