# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-08-23 20:59
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tantalus', '0002_auto_20170823_2058'),
    ]

    operations = [
        migrations.AlterField(
            model_name='singleendfastqfile',
            name='reads_file',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reads_file', to='tantalus.SequenceDataFile'),
        ),
    ]
