# Generated by Django 2.1 on 2019-05-19 11:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cabici', '0012_auto_20190112_0515'),
    ]

    operations = [
        migrations.AddField(
            model_name='pointscore',
            name='method',
            field=models.CharField(choices=[('WMCC', 'WMCC'), ('LACC', 'LACC')], default='WMCC', max_length=10, verbose_name='Pointscore Method'),
        ),
    ]