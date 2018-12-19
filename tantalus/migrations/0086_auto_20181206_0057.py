# -*- coding: utf-8 -*-
# Generated by Django 1.11.14 on 2018-11-30 23:30
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

#jira TANTA-99

#original data does not restored after rollback of the migration
#to fix it for the debugging run at the beginning
#create table rg as (select id, library_type val from tantalus_sequencedataset);
#
#after rollback run
#update tantalus_sequencedataset
#        set reference_genome=t.val
#    from rg t
#    where tantalus_sequencedataset.id=t.id;


reference_genome_fixup = {
    'grch37': 'HG19',
    'NCBI-Build-36.1': 'HG18',
    'mm10': 'MM10',
    'hg38_no_alt': 'HG38',
    'UNALIGNED': None,
    'hg19a/jaguar/1.7.5/ens69': 'HG19',
    'NCBI-Build-37': 'HG19',
    'UNUSABLE': None,
    'hg19/1000genomes': 'HG19',
}


reference_genome_names = [
    'HG18',
    'HG19',
    'HG38',
    'MM9',
    'MM10',
]


def data_migrate(apps, class_name):
    SequenceDataset = apps.get_model('tantalus', 'SequenceDataset')
    ReferenceGenome = apps.get_model('tantalus', 'ReferenceGenome')

    for g in reference_genome_names:
        ReferenceGenome.objects.create(name=g)

    reference_genomes = dict([(l.name, l) for l in ReferenceGenome.objects.all()])

    for model in SequenceDataset.objects.all():
        name = model.xxtmp
        if name in reference_genome_fixup:
            name = reference_genome_fixup[name]
        if name is None:
            model.reference_genome = None
            print '{} -> None'.format(model.xxtmp)
        else:
            model.reference_genome = reference_genomes[name]
            print '{} -> {}'.format(model.xxtmp, model.reference_genome.name)
        model.save()


#empty function, required to rollback migration
def do0(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        #('tantalus', '0088_historicalreferencegenome_referencegenome'),
        ('tantalus', '0085_auto_20181206_0054'),
    ]

    # -- rename "reference_genome" to "xxtmp"
    # -- create FK "reference_genome" (vocabulary)
    # -- fill vocabulary with unique values from "reference_genome"
    # -- set "reference_genome" FK to values based on "xxtmp" and vocabulary
    # -- remove "xxtmp"
    operations = [
        migrations.CreateModel(
            name='HistoricalReferenceGenome',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('name', models.CharField(blank=True, db_index=True, max_length=50)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
                'verbose_name': 'historical reference genome',
            },
        ),
        migrations.CreateModel(
            name='ReferenceGenome',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=50, unique=True)),
            ],
        ),

        migrations.RenameField(
            model_name='sequencedataset',
            old_name = 'reference_genome',
            new_name = 'xxtmp'
        ),
        migrations.AddField(
            model_name='SequenceDataset',
            name='reference_genome',
            field=models.ForeignKey(null=True,on_delete=django.db.models.deletion.CASCADE,
                                    to='tantalus.ReferenceGenome'),
        ),
        migrations.RunPython(data_migrate, do0),
        migrations.RemoveField(
            model_name='sequencedataset',
            name='xxtmp'
        ),
    ]
