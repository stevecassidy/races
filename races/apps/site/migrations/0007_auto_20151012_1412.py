# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('site', '0006_rider_official'),
    ]

    operations = [
        migrations.CreateModel(
            name='PointScore',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('points', models.CommaSeparatedIntegerField(default=b'7, 5, 3', max_length=100, verbose_name=b'Points for larger races')),
                ('smallpoints', models.CommaSeparatedIntegerField(default=b'5, 3', max_length=100, verbose_name=b'Points for small races')),
                ('smallthreshold', models.IntegerField(default=12, verbose_name=b'Small Race Threshold')),
                ('participation', models.IntegerField(default=2, verbose_name=b'Points for participation')),
                ('club', models.ForeignKey(to='site.Club')),
                ('races', models.ManyToManyField(to='site.Race')),
            ],
        ),
        migrations.CreateModel(
            name='ResultPoints',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('points', models.IntegerField()),
                ('pointscore', models.ForeignKey(to='site.PointScore')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='raceresult',
            unique_together=set([('race', 'grade', 'number'), ('race', 'rider')]),
        ),
        migrations.AddField(
            model_name='resultpoints',
            name='result',
            field=models.ForeignKey(to='site.RaceResult'),
        ),
    ]
