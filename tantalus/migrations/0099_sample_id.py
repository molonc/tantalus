# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

#jira TANTA-153

#tables referencing tantalus_sample(sample_id):
#   tantalus_submission(sample_id), tantalus_sequencedataset(sample_id),
#   tantalus_sample_projects(sample_id), tantalus_resultsdataset_samples(sample_id)
#but
#tantalus_sequencedataset is the only table containing data that should be updated
#
#original data does not restored after rollback of the migration
#to fix it for the debugging run at the beginning
#   create table t153sample as (select * from tantalus_sample);
#   create table t153sequencedataset as (select id,sample_id from tantalus_sequencedataset);
#
#after migration rollback run
#insert into tantalus_sample ( -- insert deleted records
#    select * from t153sample
#        where id not in (select id from tantalus_sample));
#
#update tantalus_sequencedataset s -- restore updated data
#    set sample_id=t.sample_id
#  from t153sequencedataset t
#  where s.id=t.id
#    and s.sample_id!=t.sample_id;


sample_id_fixup = {
     'MT0904'    : 'SA221' 
    ,'MT0365'    : 'SA232' 
    ,'MT1804'    : 'SA285' 
    ,'MT1584'    : 'SA290' 
    ,'MT1466'    : 'SA288' 
    ,'MT0240'    : 'SA239' 
    ,'MT1660'    : 'SA300' 
    ,'MT0904'    : 'SA221N'
    ,'MT0365'    : 'SA232N'
    ,'MT0240'    : 'SA239N'
    ,'MT2988'    : 'SA423' 
    ,'MT2932'    : 'SA425' 
    ,'MT2988'    : 'SA423N'
    ,'MT2932'    : 'SA425N'
    ,'MT3120'    : 'SA409' 
    ,'MT2851'    : 'SA420' 
    ,'MT1144'    : 'SA296' 
    ,'MT3120_BC' : 'SA409N'
    ,'MT2851_BC' : 'SA420N'
    ,'MT1804 _BC': 'SA285N'
    ,'MT1584 _BC': 'SA290N'
    ,'MT1466 _BC': 'SA288N'
}


#renames sample_from |-> sample_to,
#deletes record sample_from
def data_migrate(apps, class_name):
    Sample = apps.get_model('tantalus', 'Sample')
    SequenceDataset = apps.get_model('tantalus', 'SequenceDataset')

    for k,v in sample_id_fixup.iteritems():
        sample_from = Sample.objects.get(sample_id=k)
        sample_to   = Sample.objects.get(sample_id=v).id
        for sd in SequenceDataset.objects.filter(sample_id=sample_from.id):
            sd.sample_id = sample_to
            sd.save()

        sample_from.delete()

#empty function, required to rollback migration
def do0(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('tantalus', '0098_auto_20190110_2305'),
    ]

    # -- rename "reference_genome" to "temp_reference_genome"
    # -- create FK "reference_genome" (vocabulary)
    # -- fill vocabulary with unique values from "reference_genome"
    # -- set "reference_genome" FK to values based on "temp_reference_genome" and vocabulary
    # -- remove "temp_reference_genome"
    operations = [
        migrations.RunPython(data_migrate, do0),
    ]
