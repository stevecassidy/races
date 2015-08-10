# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('site', '0002_rider'),
    ]

    operations = [
        migrations.CreateModel(
            name='RaceResult',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('grade', models.CharField(max_length=b'10', verbose_name=b'Grade')),
                ('number', models.IntegerField(verbose_name=b'Bib Number')),
                ('place', models.IntegerField(default=0, help_text=b'Enter finishing position (eg. 1-5) or 0 for a result out of the placings.', verbose_name=b'Place')),
                ('dnf', models.BooleanField(default=False, verbose_name=b'DNF')),
                ('race', models.ForeignKey(to='site.Race')),
                ('rider', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['race', 'grade', 'number'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='raceresult',
            unique_together=set([('grade', 'number'), ('race', 'rider')]),
        ),
    ]
