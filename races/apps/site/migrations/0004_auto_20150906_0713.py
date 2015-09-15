# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('site', '0003_auto_20150810_1447'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='raceresult',
            options={'ordering': ['race', 'grade', 'place', 'number']},
        ),
        migrations.AlterField(
            model_name='raceresult',
            name='place',
            field=models.IntegerField(help_text=b'Enter finishing position (eg. 1-5), leave blank for a result out of the placings.', verbose_name=b'Place', blank=True),
        ),
        migrations.AlterField(
            model_name='raceresult',
            name='rider',
            field=models.ForeignKey(to='site.Rider'),
        ),
        migrations.AlterField(
            model_name='rider',
            name='club',
            field=models.ForeignKey(to='site.Club', null=True),
        ),
    ]
