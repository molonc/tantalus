# Generated by Django 2.2 on 2020-03-01 14:08

from django.db import migrations


def remove_old_suffix(apps, schema_editor):
    Analysis = apps.get_model('tantalus', 'Analysis')

    for a in Analysis.objects.all():
        if a.name.endswith('_old'):
            a.name = a.name[:-4]
            a.save()


class Migration(migrations.Migration):

    dependencies = [
        ('tantalus', '0128_auto_20200227_1927'),
    ]

    operations = [
        migrations.RunPython(remove_old_suffix)
    ]