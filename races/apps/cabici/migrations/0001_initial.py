# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-09-06 11:12
from __future__ import unicode_literals

import datetime
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import djangoyearlessdate.models
import geoposition.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Club',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('website', models.URLField(max_length=400)),
                ('slug', models.SlugField()),
                ('contact', models.EmailField(blank=True, max_length=254)),
                ('icalurl', models.URLField(blank=True, default=b'', max_length=400)),
                ('icalpatterns', models.CharField(blank=True, default=b'', max_length=100)),
                ('manage_races', models.BooleanField(default=False)),
                ('manage_members', models.BooleanField(default=False)),
                ('manage_results', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='ClubGrade',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('grade', models.CharField(max_length=10, verbose_name=b'Grade')),
                ('club', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cabici.Club')),
            ],
            options={
                'ordering': ['rider', 'grade'],
            },
        ),
        migrations.CreateModel(
            name='ClubRole',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name=b'Name')),
            ],
        ),
        migrations.CreateModel(
            name='Membership',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', djangoyearlessdate.models.YearField(blank=True, null=True)),
                ('category', models.CharField(choices=[(b'Ride', b'ride'), (b'Race', b'race'), (b'Non-riding', b'non-riding')], max_length=10)),
                ('club', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='cabici.Club')),
            ],
        ),
        migrations.CreateModel(
            name='PointScore',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('points', models.CommaSeparatedIntegerField(default=b'7,6,5,4,3', max_length=100, verbose_name=b'Points for larger races')),
                ('smallpoints', models.CommaSeparatedIntegerField(default=b'5,3', max_length=100, verbose_name=b'Points for small races')),
                ('smallthreshold', models.IntegerField(default=12, verbose_name=b'Small Race Threshold')),
                ('participation', models.IntegerField(default=2, verbose_name=b'Points for participation')),
                ('club', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cabici.Club')),
            ],
        ),
        migrations.CreateModel(
            name='PointscoreTally',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('points', models.IntegerField(default=0)),
                ('eventcount', models.IntegerField(default=0)),
                ('pointscore', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cabici.PointScore')),
            ],
        ),
        migrations.CreateModel(
            name='Race',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100)),
                ('date', models.DateField(help_text=b' ')),
                ('signontime', models.TimeField(help_text=b'')),
                ('starttime', models.CharField(help_text=b'', max_length=100)),
                ('website', models.URLField(blank=True, help_text=b' ', max_length=400)),
                ('status', models.CharField(choices=[(b'd', b'Draft'), (b'p', b'Published'), (b'w', b'Withdrawn')], default=b'p', help_text=b' ', max_length=1)),
                ('description', models.TextField(blank=True, default=b'', help_text=b' ')),
                ('hash', models.CharField(blank=True, max_length=100)),
                ('club', models.ForeignKey(help_text=b' ', on_delete=django.db.models.deletion.CASCADE, related_name='races', to='cabici.Club')),
            ],
            options={
                'ordering': ['date', 'signontime'],
            },
        ),
        migrations.CreateModel(
            name='RaceCourse',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('location', geoposition.fields.GeopositionField(max_length=42)),
            ],
        ),
        migrations.CreateModel(
            name='RacePrototype',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100)),
                ('time', models.TimeField()),
                ('club', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cabici.Club')),
                ('location', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cabici.RaceCourse')),
            ],
        ),
        migrations.CreateModel(
            name='RaceResult',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('grade', models.CharField(max_length=10, verbose_name=b'Grade')),
                ('number', models.IntegerField(blank=True, null=True, verbose_name=b'Bib Number')),
                ('place', models.IntegerField(blank=True, help_text=b'Enter finishing position (eg. 1-5), leave blank for a result out of the placings.', null=True, verbose_name=b'Place')),
                ('dnf', models.BooleanField(default=False, verbose_name=b'DNF')),
                ('race', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cabici.Race')),
            ],
            options={
                'ordering': ['race', 'grade', 'place', 'number'],
            },
        ),
        migrations.CreateModel(
            name='RaceStaff',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('race', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='officials', to='cabici.Race')),
            ],
        ),
        migrations.CreateModel(
            name='Rider',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('licenceno', models.CharField(max_length=20, verbose_name=b'Licence Number')),
                ('gender', models.CharField(choices=[(b'M', b'M'), (b'F', b'F')], max_length=2, verbose_name=b'Gender')),
                ('dob', models.DateField(default=datetime.date(1970, 1, 1), verbose_name=b'Date of Birth')),
                ('streetaddress', models.CharField(default=b'', max_length=100, verbose_name=b'Address')),
                ('suburb', models.CharField(default=b'', max_length=100, verbose_name=b'Suburb')),
                ('state', models.CharField(choices=[(b'ACT', b'Australian Capital Territory'), (b'NSW', b'New South Wales'), (b'NT', b'Northern Territory'), (b'QLD', b'Queensland'), (b'SA', b'South Australia'), (b'TAS', b'Tasmania'), (b'VIC', b'Victoria'), (b'WA', b'Western Australia')], default=b'NSW', max_length=10, verbose_name=b'State')),
                ('postcode', models.CharField(default=b'', max_length=4, verbose_name=b'Postcode')),
                ('phone', models.CharField(default=b'', max_length=50, verbose_name=b'Phone')),
                ('commissaire', models.CharField(default=b'0', help_text=b'0 if not a Commissaire, otherwise eg. 1, RT', max_length=10, verbose_name=b'Commissaire Level')),
                ('commissaire_valid', models.DateField(blank=True, null=True, verbose_name=b'Commissaire Valid To')),
                ('emergencyname', models.CharField(default=b'', max_length=100, verbose_name=b'Emergency Contact Name')),
                ('emergencyphone', models.CharField(default=b'', max_length=50, verbose_name=b'Emergency Contact Phone')),
                ('emergencyrelationship', models.CharField(default=b'', max_length=20, verbose_name=b'Emergency Contact Relationship')),
                ('official', models.BooleanField(default=False, help_text=b'Officials can view and edit member details, schedule races, upload results', verbose_name=b'Club Official')),
                ('club', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='cabici.Club')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='UserRole',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('club', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cabici.Club')),
                ('role', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cabici.ClubRole')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='racestaff',
            name='rider',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cabici.Rider'),
        ),
        migrations.AddField(
            model_name='racestaff',
            name='role',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cabici.ClubRole'),
        ),
        migrations.AddField(
            model_name='raceresult',
            name='rider',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cabici.Rider'),
        ),
        migrations.AddField(
            model_name='race',
            name='location',
            field=models.ForeignKey(help_text=b' ', on_delete=django.db.models.deletion.CASCADE, to='cabici.RaceCourse'),
        ),
        migrations.AddField(
            model_name='pointscoretally',
            name='rider',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cabici.Rider'),
        ),
        migrations.AddField(
            model_name='pointscore',
            name='races',
            field=models.ManyToManyField(blank=True, to='cabici.Race'),
        ),
        migrations.AddField(
            model_name='membership',
            name='rider',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cabici.Rider'),
        ),
        migrations.AddField(
            model_name='clubgrade',
            name='rider',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cabici.Rider'),
        ),
        migrations.AlterUniqueTogether(
            name='raceresult',
            unique_together=set([('race', 'grade', 'number'), ('race', 'rider')]),
        ),
    ]
