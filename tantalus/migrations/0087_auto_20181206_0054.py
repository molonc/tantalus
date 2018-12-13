# -*- coding: utf-8 -*-
# Generated by Django 1.11.14 on 2018-12-05 00:30
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.core.exceptions import ObjectDoesNotExist


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


#value list is based on database 2018-11-29
type_map = {
     'nan'                                  : None
    ,''                                     : None
    ,'micro RNA'                            : 'MIRNA'
    ,'Amplicon-SLX-PET'                     : 'DNA_AMPLICON'
    ,'Methylation sensitive restriction'    : 'MRE'
    ,'Methylated DNA immunoprecipitation'   : 'MEDIP'
    ,'Chromatin Immunoprecipitation'        : 'CHIP'
    ,'Bisulfite'                            : 'BISULFITE'
    #,'RNASEQ'                               : 'RNASEQ'
    #,'WGS'                                  : 'WGS'
}

def translate(val):
    x = val
    if x:
        x = x.strip()
    #print('-%s;' % (x))
    if (x in type_map):
        x = type_map[x]
    #print('+%s;' % (x))
    return x

def migrate_data(apps,class_name):

    seqds = apps.get_model('tantalus',class_name)
    vocab = apps.get_model('tantalus','LibraryType')

    recs = seqds.objects.values_list('xxtmp',flat=True).distinct()

    print("\n\n%s;\n  N=%i;\n" % (str(recs.query),recs.count()))

    #fill vocabulary, ignore existing values
    for x in recs:
        x = translate(x)
        if (x):
            y = vocab.objects.get_or_create(name=x)
            #print("voc: %s;" % (x))

    recs = seqds.objects.all()

    print("\n\n%s;\n  N=%i;\n" % (str(recs.query),recs.count()))
    for r in recs:
        try:
            #print("%d; %s;" % (r.id,r.xxtmp))
            v = vocab.objects.get(name=translate(r.xxtmp))
            r.library_type = v
            r.save()
            if (0 == (r.id % 113)):
                print("----- %s; %s;" % (r.id,r.library_type.id))
        except ObjectDoesNotExist:
            pass

def migrate_submission(apps, schema_editor):
    migrate_data(apps,'Submission')

def migrate_dnalibrary(apps, schema_editor):
    migrate_data(apps,'DNALibrary')

#empty function, required to rollback migration
def do0(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('tantalus', '0084_patient_case_id'),
    ]

    # -- rename "library_type" to "xxtmp"
    # -- create FK "library_type" (vocabulary)
    # -- fill vocabulary with unique values from "library_type"
    # -- set "library_type" FK to values based on "xxtmp" and vocabulary
    # -- remove "xxtmp"
    operations = [

        migrations.CreateModel(
            name='LibraryType',
            fields=[('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                    ('name', models.CharField(max_length=240, blank=True, null=False, unique=True)), ]),

        #Submission
        migrations.RenameField(
            model_name='Submission',
            old_name = 'library_type',
            new_name = 'xxtmp'
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
            name='xxtmp',
        ),

        #DNALibrary
        migrations.AlterField(
            model_name='historicaldnalibrary',
            name='library_type',
            #field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='tantalus.LibraryType'),
            field=models.CharField(blank=True, null=True, max_length=240),
        ),
        #migrations.AlterField(
        #    model_name='historicaldnalibrary',
        #    name='library_type',
        #    field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='tantalus.LibraryType'),
        #),
        migrations.AlterField(
            model_name='DNALibrary',
            name='library_type',
            field=models.CharField(null=True,blank=True,default='',max_length=240)
        ),
        migrations.RenameField(
            model_name='DNALibrary',
            old_name = 'library_type',
            new_name = 'xxtmp'
        ),
        migrations.AddField(
            model_name='DNALibrary',
            name='library_type',
            field=models.ForeignKey(null=True,on_delete=django.db.models.deletion.CASCADE,
                                    to='tantalus.LibraryType'),
        ),
        migrations.RunPython(
            migrate_dnalibrary,
            do0
        ),
        migrations.RemoveField(
            model_name='DNALibrary',
            name='xxtmp'
        ),
    ]

