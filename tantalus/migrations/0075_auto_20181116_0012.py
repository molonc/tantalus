# -*- coding: utf-8 -*-
# Generated by Django 1.11.14 on 2018-11-16 00:12
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tantalus', '0074_auto_20181104_1927'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalsample',
            name='collaborator',
            field=models.CharField(max_length=240, null=True),
        ),
        migrations.AddField(
            model_name='historicalsample',
            name='submitter',
            field=models.CharField(max_length=240, null=True),
        ),
        migrations.AddField(
            model_name='patient',
            name='external_patient_id',
            field=models.CharField(max_length=120, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='sample',
            name='collaborator',
            field=models.CharField(max_length=240, null=True),
        ),
        migrations.AddField(
            model_name='sample',
            name='submitter',
            field=models.CharField(max_length=240, null=True),
        ),
        migrations.AlterField(
            model_name='sample',
            name='projects',
            field=models.ManyToManyField(blank=True, to='tantalus.Project'),
        ),
    ]