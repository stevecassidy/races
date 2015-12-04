# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('site', '0011_userrole'),
    ]

    operations = [
        migrations.AddField(
            model_name='userrole',
            name='club',
            field=models.ForeignKey(default=74, to='site.Club'),
            preserve_default=False,
        ),
    ]
