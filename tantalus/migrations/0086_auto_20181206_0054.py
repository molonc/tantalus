# -*- coding: utf-8 -*-
# Generated by Django 1.11.14 on 2018-12-05 00:30
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


#jira TANTA-2, TANTA-128, TANTA-151

#original data does not restored after rollback of the migration
#to fix it for the debugging run at the beginning
#create table tts as (select id, library_type val from tantalus_submission);
#create table ttl as (select id, library_type val from tantalus_dnalibrary);
#
#after rollback run
#update tantalus_dnalibrary s
#    set library_type=t.val
#    from ttl t
#    where t.id = s.id;
#
#update tantalus_submission s
#    set library_type=t.val
#    from tts t
#    where t.id = s.id;
#

EXOME = 'EXOME'
WGS = 'WGS'
RNASEQ = 'RNASEQ'
SINGLE_CELL_WGS = 'SC_WGS'
SINGLE_CELL_RNASEQ = 'SC_RNASEQ'
EXCAP = 'EXCAP'
BISULFITE = 'BISULFITE'
CHIP = 'CHIP'
MRE = 'MRE'
MIRNA = 'MIRNA'
MEDIP = 'MEDIP'
DNA_AMPLICON = 'DNA_AMPLICON'

library_type_choices = (
    (EXOME, 'Bulk Whole Exome Sequence'),
    (WGS, 'Bulk Whole Genome Sequence'),
    (RNASEQ, 'Bulk RNA-Seq'),
    (SINGLE_CELL_WGS, 'Single Cell Whole Genome Sequence'),
    (SINGLE_CELL_RNASEQ, 'Single Cell RNA-Seq'),
    (EXCAP,'Exon Capture'),
    (MIRNA,'micro RNA'),
    (BISULFITE,'Bisulfite'),
    (CHIP,'Chromatin Immunoprecipitation'),
    (MRE,'Methylation sensitive restriction enzyme sequencing'),
    (MEDIP,'Methylated DNA immunoprecipitation'),
    (DNA_AMPLICON,'Targetted DNA Amplicon Sequence')
)


def populate_library_type(apps, schema_editor):
    LibraryType = apps.get_model('tantalus', 'LibraryType')

    for k, v in library_type_choices:
        LibraryType.objects.create(name=k, description=v)


library_type_fixup = {
    'nan'                                  : None,
    ''                                     : None,
    ' '                                    : None,
    'micro RNA'                            : 'MIRNA',
    'Amplicon-SLX-PET'                     : 'DNA_AMPLICON',
    'Methylation sensitive restriction'    : 'MRE',
    'Methylated DNA immunoprecipitation'   : 'MEDIP',
    'Chromatin Immunoprecipitation'        : 'CHIP',
    'Bisulfite'                            : 'BISULFITE',
}


def migrate_data(apps, class_name):
    MigratingModel = apps.get_model('tantalus', class_name)
    LibraryType = apps.get_model('tantalus', 'LibraryType')

    library_types = dict([(l.name, l) for l in LibraryType.objects.all()])

    for model in MigratingModel.objects.all():
        name = model.temp_library_type
        if name in library_type_fixup:
            name = library_type_fixup[name]
        if name is None:
            model.library_type = None
            print '{} -> None'.format(model.temp_library_type)
        else:
            model.library_type = library_types[name]
            print '{} -> {}'.format(model.temp_library_type, model.library_type.name)
        model.save()


def migrate_submission(apps, schema_editor):
    migrate_data(apps,'Submission')


def migrate_dnalibrary(apps, schema_editor):
    migrate_data(apps,'DNALibrary')


#empty function, required to rollback migration
def do0(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('tantalus', '0085_auto_20181220_0005'),
    ]

    # -- rename "library_type" to "temp_library_type"
    # -- create FK "library_type" (vocabulary)
    # -- fill vocabulary with unique values from "library_type"
    # -- set "library_type" FK to values based on "temp_library_type" and vocabulary
    # -- remove "temp_library_type"
    operations = [
        migrations.CreateModel(
            name='HistoricalLibraryType',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('name', models.CharField(blank=True, db_index=True, max_length=50)),
                ('description', models.CharField(blank=True, db_index=True, max_length=240)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
                'verbose_name': 'historical library type',
            },
        ),
        migrations.CreateModel(
            name='LibraryType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=50, unique=True)),
                ('description', models.CharField(blank=True, max_length=240, unique=True)),
            ],
        ),
        migrations.RunPython(
            populate_library_type,
            do0
        ),

        # Submission
        migrations.RenameField(
            model_name='Submission',
            old_name = 'library_type',
            new_name = 'temp_library_type'
        ),
        migrations.AddField(
            model_name='Submission',
            name='library_type',
            field=models.ForeignKey(null=True,on_delete=django.db.models.deletion.CASCADE,
                                    to='tantalus.LibraryType'),
        ),
        migrations.RunPython(
            migrate_submission,
            do0
        ),
        migrations.RemoveField(
            model_name='Submission',
            name='temp_library_type',
        ),

        # DNALibrary
        migrations.RenameField(
            model_name='historicaldnalibrary',
            old_name='library_type',
            new_name='temp_library_type',
        ),
        migrations.RenameField(
            model_name='DNALibrary',
            old_name='library_type',
            new_name='temp_library_type'
        ),
        migrations.AddField(
            model_name='DNALibrary',
            name='library_type',
            field=models.ForeignKey(null=True,on_delete=django.db.models.deletion.CASCADE, to='tantalus.LibraryType'),
        ),
        migrations.AddField(
            model_name='historicaldnalibrary',
            name='library_type',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='tantalus.LibraryType'),
        ),
        migrations.RunPython(
            migrate_dnalibrary,
            do0
        ),
        migrations.RemoveField(
            model_name='DNALibrary',
            name='temp_library_type'
        ),
        migrations.RemoveField(
            model_name='historicaldnalibrary',
            name='temp_library_type',
        ),
    ]
