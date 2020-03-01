# Generated by Django 2.2 on 2020-02-27 19:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tantalus', '0127_auto_20200127_2101'),
    ]

    operations = [
        migrations.AlterField(
            model_name='analysis',
            name='name',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='historicalanalysis',
            name='name',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterUniqueTogether(
            name='analysis',
            unique_together={('name', 'jira_ticket')},
        ),
    ]
