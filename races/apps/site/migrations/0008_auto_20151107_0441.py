# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('site', '0007_auto_20151012_1412'),
    ]

    operations = [
        migrations.RenameField(
            model_name='club',
            old_name='url',
            new_name='website',
        ),
        migrations.RenameField(
            model_name='race',
            old_name='url',
            new_name='website',
        ),
        migrations.AlterField(
            model_name='pointscore',
            name='points',
            field=models.CommaSeparatedIntegerField(default=b'7,6,5,4,3', max_length=100, verbose_name=b'Points for larger races'),
        ),
        migrations.AlterField(
            model_name='pointscore',
            name='smallpoints',
            field=models.CommaSeparatedIntegerField(default=b'5,3', max_length=100, verbose_name=b'Points for small races'),
        ),
        migrations.AlterField(
            model_name='race',
            name='club',
            field=models.ForeignKey(related_name='races', to='site.Club'),
        ),
    ]
