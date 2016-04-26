# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-04-13 11:03
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('site', '0018_auto_20160410_1507'),
    ]

    operations = [
        migrations.AddField(
            model_name='membership',
            name='category',
            field=models.CharField(choices=[(b'Ride', b'ride'), (b'Race', b'race'), (b'Non-riding', b'non-riding')], default='race', max_length=10),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='race',
            name='signontime',
            field=models.TimeField(help_text=b''),
        ),
        migrations.AlterField(
            model_name='race',
            name='starttime',
            field=models.CharField(help_text=b'', max_length=100),
        ),
        migrations.AlterField(
            model_name='race',
            name='status',
            field=models.CharField(choices=[(b'd', b'Draft'), (b'p', b'Published'), (b'w', b'Withdrawn')], default=b'p', help_text=b' ', max_length=1),
        ),
    ]