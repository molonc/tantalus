# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-08-11 19:54
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import taggit.managers


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('taggit', '0003_historicaltag'),
    ]

    operations = [
        migrations.CreateModel(
            name='Deployment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('state', models.CharField(max_length=50, null=True, verbose_name='State')),
                ('result', models.IntegerField(null=True, verbose_name='Result')),
            ],
        ),
        migrations.CreateModel(
            name='DNALibrary',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('library_id', models.CharField(max_length=50, verbose_name='Library ID')),
                ('library_type', models.CharField(choices=[('Exome', 'Bulk Whole Exome Sequence'), ('WGS', 'Bulk Whole Genome Sequence'), ('SC WGS', 'Single Cell Whole Genome Sequence'), ('RNA-Seq', 'Bulk RNA-Seq'), ('SC RNA-Seq', 'Single Cell RNA-Seq')], max_length=50, verbose_name='Library Type')),
            ],
        ),
        migrations.CreateModel(
            name='DNASequences',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('index_format', models.CharField(blank=True, choices=[('S', 'Single'), ('D', 'Dual')], max_length=50, null=True, verbose_name='Index Format')),
                ('index_sequence', models.CharField(blank=True, max_length=50, null=True, verbose_name='Index Sequence')),
                ('dna_library', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tantalus.DNALibrary')),
            ],
        ),
        migrations.CreateModel(
            name='FileInstance',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('filename', models.CharField(max_length=500, verbose_name='Filename')),
            ],
        ),
        migrations.CreateModel(
            name='FileTransfer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('state', models.CharField(max_length=50, null=True, verbose_name='State')),
                ('result', models.IntegerField(null=True, verbose_name='Result')),
            ],
        ),
        migrations.CreateModel(
            name='HistoricalAzureBlobStorage',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
                ('storage_account', models.CharField(max_length=50, verbose_name='Storage Account')),
                ('storage_container', models.CharField(max_length=50, verbose_name='Storage Container')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('polymorphic_ctype', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='contenttypes.ContentType')),
            ],
            options={
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
                'verbose_name': 'historical azure blob storage',
            },
        ),
        migrations.CreateModel(
            name='HistoricalBamFile',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('reference_genome', models.CharField(choices=[('hg19', 'Human Genome 19'), ('hg18', 'Human Genome 18'), ('none', 'Unaligned')], max_length=50, verbose_name='Reference Genome')),
                ('aligner', models.CharField(max_length=50, verbose_name='Aligner')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
            ],
            options={
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
                'verbose_name': 'historical bam file',
            },
        ),
        migrations.CreateModel(
            name='HistoricalDNALibrary',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('library_id', models.CharField(max_length=50, verbose_name='Library ID')),
                ('library_type', models.CharField(choices=[('Exome', 'Bulk Whole Exome Sequence'), ('WGS', 'Bulk Whole Genome Sequence'), ('SC WGS', 'Single Cell Whole Genome Sequence'), ('RNA-Seq', 'Bulk RNA-Seq'), ('SC RNA-Seq', 'Single Cell RNA-Seq')], max_length=50, verbose_name='Library Type')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
                'verbose_name': 'historical dna library',
            },
        ),
        migrations.CreateModel(
            name='HistoricalDNASequences',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('index_format', models.CharField(blank=True, choices=[('S', 'Single'), ('D', 'Dual')], max_length=50, null=True, verbose_name='Index Format')),
                ('index_sequence', models.CharField(blank=True, max_length=50, null=True, verbose_name='Index Sequence')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('dna_library', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='tantalus.DNALibrary')),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
                'verbose_name': 'historical dna sequences',
            },
        ),
        migrations.CreateModel(
            name='HistoricalFileInstance',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('filename', models.CharField(max_length=500, verbose_name='Filename')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
            ],
            options={
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
                'verbose_name': 'historical file instance',
            },
        ),
        migrations.CreateModel(
            name='HistoricalPairedEndFastqFiles',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('polymorphic_ctype', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='contenttypes.ContentType')),
            ],
            options={
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
                'verbose_name': 'historical paired end fastq files',
            },
        ),
        migrations.CreateModel(
            name='HistoricalSample',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('sample_id_space', models.CharField(choices=[('SA', 'Aparicio'), ('DG', 'Huntsman'), ('O', 'Other')], max_length=50, verbose_name='Sample ID Space')),
                ('sample_id', models.CharField(max_length=50, verbose_name='Sample ID')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
                'verbose_name': 'historical sample',
            },
        ),
        migrations.CreateModel(
            name='HistoricalSequenceDataFile',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('md5', models.CharField(max_length=50, verbose_name='MD5')),
                ('size', models.BigIntegerField(verbose_name='Size')),
                ('created', models.DateTimeField(verbose_name='Created')),
                ('file_type', models.CharField(choices=[('BAM', 'BAM'), ('BAI', 'BAM Index'), ('FQ', 'Fastq')], max_length=50, verbose_name='Type')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
                'verbose_name': 'historical sequence data file',
            },
        ),
        migrations.CreateModel(
            name='HistoricalSequenceDataset',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('polymorphic_ctype', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='contenttypes.ContentType')),
            ],
            options={
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
                'verbose_name': 'historical sequence dataset',
            },
        ),
        migrations.CreateModel(
            name='HistoricalSequenceLane',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('flowcell_id', models.CharField(max_length=50, verbose_name='FlowCell ID')),
                ('lane_number', models.PositiveSmallIntegerField(verbose_name='Lane Number')),
                ('sequencing_centre', models.CharField(max_length=50, verbose_name='Sequencing Centre')),
                ('sequencing_library_id', models.CharField(max_length=50, verbose_name='Sequencing Library ID')),
                ('sequencing_instrument', models.CharField(choices=[('HX', 'HiSeqX'), ('H2500', 'HiSeq2500'), ('N550', 'NextSeq550'), ('MI', 'MiSeq'), ('O', 'other')], max_length=50, verbose_name='Sequencing instrument')),
                ('read_type', models.CharField(choices=[('P', 'PET'), ('S', 'SET')], max_length=50, verbose_name='Read type')),
                ('index_read_type', models.CharField(choices=[('D', 'Dual Index (i7 and i5)'), ('N', 'No Indexing')], max_length=50, verbose_name='Index read type')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('dna_library', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='tantalus.DNALibrary')),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
                'verbose_name': 'historical sequence lane',
            },
        ),
        migrations.CreateModel(
            name='HistoricalServerStorage',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
                ('server_ip', models.CharField(max_length=50, verbose_name='Server IP')),
                ('storage_directory', models.CharField(max_length=500, verbose_name='Storage Directory')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('polymorphic_ctype', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='contenttypes.ContentType')),
            ],
            options={
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
                'verbose_name': 'historical server storage',
            },
        ),
        migrations.CreateModel(
            name='HistoricalSingleEndFastqFile',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('polymorphic_ctype', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='contenttypes.ContentType')),
            ],
            options={
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
                'verbose_name': 'historical single end fastq file',
            },
        ),
        migrations.CreateModel(
            name='HistoricalStorage',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('polymorphic_ctype', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='contenttypes.ContentType')),
            ],
            options={
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
                'verbose_name': 'historical storage',
            },
        ),
        migrations.CreateModel(
            name='Sample',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sample_id_space', models.CharField(choices=[('SA', 'Aparicio'), ('DG', 'Huntsman'), ('O', 'Other')], max_length=50, verbose_name='Sample ID Space')),
                ('sample_id', models.CharField(max_length=50, verbose_name='Sample ID')),
            ],
        ),
        migrations.CreateModel(
            name='SequenceDataFile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('md5', models.CharField(max_length=50, verbose_name='MD5')),
                ('size', models.BigIntegerField(verbose_name='Size')),
                ('created', models.DateTimeField(verbose_name='Created')),
                ('file_type', models.CharField(choices=[('BAM', 'BAM'), ('BAI', 'BAM Index'), ('FQ', 'Fastq')], max_length=50, verbose_name='Type')),
            ],
        ),
        migrations.CreateModel(
            name='SequenceDataset',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SequenceLane',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('flowcell_id', models.CharField(max_length=50, verbose_name='FlowCell ID')),
                ('lane_number', models.PositiveSmallIntegerField(verbose_name='Lane Number')),
                ('sequencing_centre', models.CharField(max_length=50, verbose_name='Sequencing Centre')),
                ('sequencing_library_id', models.CharField(max_length=50, verbose_name='Sequencing Library ID')),
                ('sequencing_instrument', models.CharField(choices=[('HX', 'HiSeqX'), ('H2500', 'HiSeq2500'), ('N550', 'NextSeq550'), ('MI', 'MiSeq'), ('O', 'other')], max_length=50, verbose_name='Sequencing instrument')),
                ('read_type', models.CharField(choices=[('P', 'PET'), ('S', 'SET')], max_length=50, verbose_name='Read type')),
                ('index_read_type', models.CharField(choices=[('D', 'Dual Index (i7 and i5)'), ('N', 'No Indexing')], max_length=50, verbose_name='Index read type')),
                ('dna_library', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tantalus.DNALibrary')),
            ],
        ),
        migrations.CreateModel(
            name='Storage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='AzureBlobStorage',
            fields=[
                ('storage_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='tantalus.Storage')),
                ('storage_account', models.CharField(max_length=50, verbose_name='Storage Account')),
                ('storage_container', models.CharField(max_length=50, verbose_name='Storage Container')),
            ],
            options={
                'abstract': False,
            },
            bases=('tantalus.storage',),
        ),
        migrations.CreateModel(
            name='BamFile',
            fields=[
                ('sequencedataset_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='tantalus.SequenceDataset')),
                ('reference_genome', models.CharField(choices=[('hg19', 'Human Genome 19'), ('hg18', 'Human Genome 18'), ('none', 'Unaligned')], max_length=50, verbose_name='Reference Genome')),
                ('aligner', models.CharField(max_length=50, verbose_name='Aligner')),
                ('bam_file', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bam_file', to='tantalus.SequenceDataFile')),
                ('bam_index_file', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bam_index_file', to='tantalus.SequenceDataFile')),
            ],
            options={
                'abstract': False,
            },
            bases=('tantalus.sequencedataset',),
        ),
        migrations.CreateModel(
            name='PairedEndFastqFiles',
            fields=[
                ('sequencedataset_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='tantalus.SequenceDataset')),
                ('reads_1_file', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reads_1_file', to='tantalus.SequenceDataFile')),
                ('reads_2_file', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reads_2_file', to='tantalus.SequenceDataFile')),
            ],
            options={
                'abstract': False,
            },
            bases=('tantalus.sequencedataset',),
        ),
        migrations.CreateModel(
            name='ServerStorage',
            fields=[
                ('storage_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='tantalus.Storage')),
                ('server_ip', models.CharField(max_length=50, verbose_name='Server IP')),
                ('storage_directory', models.CharField(max_length=500, verbose_name='Storage Directory')),
            ],
            options={
                'abstract': False,
            },
            bases=('tantalus.storage',),
        ),
        migrations.CreateModel(
            name='SingleEndFastqFile',
            fields=[
                ('sequencedataset_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='tantalus.SequenceDataset')),
                ('reads_file', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reads_file', to='tantalus.SequenceDataFile')),
            ],
            options={
                'abstract': False,
            },
            bases=('tantalus.sequencedataset',),
        ),
        migrations.AddField(
            model_name='storage',
            name='polymorphic_ctype',
            field=models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='polymorphic_tantalus.storage_set+', to='contenttypes.ContentType'),
        ),
        migrations.AddField(
            model_name='sequencedataset',
            name='dna_sequences',
            field=models.ManyToManyField(to='tantalus.DNASequences', verbose_name='Sequences'),
        ),
        migrations.AddField(
            model_name='sequencedataset',
            name='lanes',
            field=models.ManyToManyField(to='tantalus.SequenceLane', verbose_name='Lanes'),
        ),
        migrations.AddField(
            model_name='sequencedataset',
            name='polymorphic_ctype',
            field=models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='polymorphic_tantalus.sequencedataset_set+', to='contenttypes.ContentType'),
        ),
        migrations.AddField(
            model_name='sequencedataset',
            name='sequence_data',
            field=models.ManyToManyField(to='tantalus.SequenceDataFile', verbose_name='Data'),
        ),
        migrations.AddField(
            model_name='sequencedataset',
            name='tags',
            field=taggit.managers.TaggableManager(help_text='A comma-separated list of tags.', through='taggit.TaggedItem', to='taggit.Tag', verbose_name='Tags'),
        ),
        migrations.AddField(
            model_name='historicalsingleendfastqfile',
            name='reads_file',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='tantalus.SequenceDataFile'),
        ),
        migrations.AddField(
            model_name='historicalsingleendfastqfile',
            name='sequencedataset_ptr',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='tantalus.SequenceDataset'),
        ),
        migrations.AddField(
            model_name='historicalserverstorage',
            name='storage_ptr',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='tantalus.Storage'),
        ),
        migrations.AddField(
            model_name='historicalpairedendfastqfiles',
            name='reads_1_file',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='tantalus.SequenceDataFile'),
        ),
        migrations.AddField(
            model_name='historicalpairedendfastqfiles',
            name='reads_2_file',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='tantalus.SequenceDataFile'),
        ),
        migrations.AddField(
            model_name='historicalpairedendfastqfiles',
            name='sequencedataset_ptr',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='tantalus.SequenceDataset'),
        ),
        migrations.AddField(
            model_name='historicalfileinstance',
            name='file_resource',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='tantalus.SequenceDataFile'),
        ),
        migrations.AddField(
            model_name='historicalfileinstance',
            name='history_user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='historicalfileinstance',
            name='storage',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='tantalus.Storage'),
        ),
        migrations.AddField(
            model_name='historicaldnasequences',
            name='sample',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='tantalus.Sample'),
        ),
        migrations.AddField(
            model_name='historicalbamfile',
            name='bam_file',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='tantalus.SequenceDataFile'),
        ),
        migrations.AddField(
            model_name='historicalbamfile',
            name='bam_index_file',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='tantalus.SequenceDataFile'),
        ),
        migrations.AddField(
            model_name='historicalbamfile',
            name='history_user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='historicalbamfile',
            name='polymorphic_ctype',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='contenttypes.ContentType'),
        ),
        migrations.AddField(
            model_name='historicalbamfile',
            name='sequencedataset_ptr',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='tantalus.SequenceDataset'),
        ),
        migrations.AddField(
            model_name='historicalazureblobstorage',
            name='storage_ptr',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='tantalus.Storage'),
        ),
        migrations.AddField(
            model_name='filetransfer',
            name='datafile',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tantalus.SequenceDataFile'),
        ),
        migrations.AddField(
            model_name='filetransfer',
            name='deployment',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tantalus.Deployment'),
        ),
        migrations.AddField(
            model_name='fileinstance',
            name='file_resource',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tantalus.SequenceDataFile'),
        ),
        migrations.AddField(
            model_name='fileinstance',
            name='storage',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tantalus.Storage'),
        ),
        migrations.AddField(
            model_name='dnasequences',
            name='sample',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tantalus.Sample'),
        ),
        migrations.AddField(
            model_name='deployment',
            name='files',
            field=models.ManyToManyField(to='tantalus.SequenceDataset', verbose_name='Datasets'),
        ),
        migrations.AddField(
            model_name='deployment',
            name='from_storage',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deployment_from_storage', to='tantalus.Storage'),
        ),
        migrations.AddField(
            model_name='deployment',
            name='to_storage',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deployment_to_storage', to='tantalus.Storage'),
        ),
    ]
