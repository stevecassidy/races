#!/usr/bin/python
#
# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2017-01-01 04:28


import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cabici', '0004_auto_20161128_0326'),
    ]

    operations = [
        migrations.AlterField(
            model_name='racecourse',
            name='shortname',
            field=models.CharField(default=b'', max_length=20),
        ),
        migrations.AlterField(
            model_name='rider',
            name='commissaire',
            field=models.CharField(blank=True, default=b'0', help_text=b'0 if not a Commissaire, otherwise eg. 1, RT', max_length=10, verbose_name=b'Commissaire Level'),
        ),
        migrations.AlterField(
            model_name='rider',
            name='dob',
            field=models.DateField(blank=True, default=datetime.date(1970, 1, 1), verbose_name=b'Date of Birth'),
        ),
        migrations.AlterField(
            model_name='rider',
            name='emergencyname',
            field=models.CharField(blank=True, default=b'', max_length=100, verbose_name=b'Emergency Contact Name'),
        ),
        migrations.AlterField(
            model_name='rider',
            name='emergencyphone',
            field=models.CharField(blank=True, default=b'', max_length=50, verbose_name=b'Emergency Contact Phone'),
        ),
        migrations.AlterField(
            model_name='rider',
            name='emergencyrelationship',
            field=models.CharField(blank=True, default=b'', max_length=20, verbose_name=b'Emergency Contact Relationship'),
        ),
        migrations.AlterField(
            model_name='rider',
            name='gender',
            field=models.CharField(blank=True, choices=[(b'M', b'Male'), (b'F', b'Female')], default=b'M', max_length=2, verbose_name=b'Gender'),
        ),
        migrations.AlterField(
            model_name='rider',
            name='licenceno',
            field=models.CharField(blank=True, default=b'', max_length=20, verbose_name=b'Licence Number'),
        ),
        migrations.AlterField(
            model_name='rider',
            name='phone',
            field=models.CharField(blank=True, default=b'', max_length=50, verbose_name=b'Phone'),
        ),
        migrations.AlterField(
            model_name='rider',
            name='postcode',
            field=models.CharField(blank=True, default=b'', max_length=4, verbose_name=b'Postcode'),
        ),
        migrations.AlterField(
            model_name='rider',
            name='state',
            field=models.CharField(blank=True, choices=[(b'ACT', b'Australian Capital Territory'), (b'NSW', b'New South Wales'), (b'NT', b'Northern Territory'), (b'QLD', b'Queensland'), (b'SA', b'South Australia'), (b'TAS', b'Tasmania'), (b'VIC', b'Victoria'), (b'WA', b'Western Australia')], default=b'NSW', max_length=10, verbose_name=b'State'),
        ),
        migrations.AlterField(
            model_name='rider',
            name='streetaddress',
            field=models.CharField(blank=True, default=b'', max_length=100, verbose_name=b'Address'),
        ),
        migrations.AlterField(
            model_name='rider',
            name='suburb',
            field=models.CharField(blank=True, default=b'', max_length=100, verbose_name=b'Suburb'),
        ),
    ]
