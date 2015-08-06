# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import geoposition.fields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Club',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('url', models.URLField(max_length=400)),
                ('slug', models.SlugField()),
                ('contact', models.EmailField(max_length=254, blank=True)),
                ('icalurl', models.URLField(default=b'', max_length=400, blank=True)),
                ('icalpatterns', models.CharField(default=b'', max_length=100, blank=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Race',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=100)),
                ('date', models.DateField()),
                ('time', models.TimeField()),
                ('url', models.URLField(max_length=400, blank=True)),
                ('status', models.CharField(default=b'd', max_length=1, choices=[(b'd', b'Draft'), (b'p', b'Published'), (b'w', b'Withdrawn')])),
                ('description', models.TextField(default=b'', blank=True)),
                ('hash', models.CharField(max_length=100, blank=True)),
                ('club', models.ForeignKey(to='site.Club')),
            ],
            options={
                'ordering': ['date', 'time'],
            },
        ),
        migrations.CreateModel(
            name='RaceCourse',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('location', geoposition.fields.GeopositionField(max_length=42)),
            ],
        ),
        migrations.CreateModel(
            name='RacePrototype',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=100)),
                ('time', models.TimeField()),
                ('club', models.ForeignKey(to='site.Club')),
                ('location', models.ForeignKey(to='site.RaceCourse')),
            ],
        ),
        migrations.AddField(
            model_name='race',
            name='location',
            field=models.ForeignKey(to='site.RaceCourse'),
        ),
    ]
