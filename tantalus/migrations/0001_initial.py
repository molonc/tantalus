# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2017-08-02 21:23
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AzureBlobFileInstance',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('storage_account', models.CharField(max_length=50, verbose_name='Storage Account')),
                ('storage_container', models.CharField(max_length=50, verbose_name='Storage Container')),
                ('filename', models.CharField(max_length=500, verbose_name='Filename')),
            ],
        ),
        migrations.CreateModel(
            name='BamFile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reference_genome', models.CharField(choices=[('hg19', 'Human Genome 19'), ('hg18', 'Human Genome 18'), ('none', 'No Useful alignments')], max_length=50, verbose_name='Reference Genome')),
                ('aligner', models.CharField(max_length=50, verbose_name='Aligner')),
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
            name='HistoricalAzureBlobFileInstance',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('storage_account', models.CharField(max_length=50, verbose_name='Storage Account')),
                ('storage_container', models.CharField(max_length=50, verbose_name='Storage Container')),
                ('filename', models.CharField(max_length=500, verbose_name='Filename')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
            ],
            options={
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
                'verbose_name': 'historical azure blob file instance',
            },
        ),
        migrations.CreateModel(
            name='HistoricalBamFile',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('reference_genome', models.CharField(choices=[('hg19', 'Human Genome 19'), ('hg18', 'Human Genome 18'), ('none', 'No Useful alignments')], max_length=50, verbose_name='Reference Genome')),
                ('aligner', models.CharField(max_length=50, verbose_name='Aligner')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
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
            name='HistoricalPairedFastqFiles',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
                'verbose_name': 'historical paired fastq files',
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
                ('created', models.DateField(verbose_name='Created')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
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
            name='HistoricalSequenceLane',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('sequencing_centre', models.CharField(max_length=50, verbose_name='Sequencing Centre')),
                ('flowcell_id', models.CharField(max_length=50, verbose_name='FlowCell ID')),
                ('lane_number', models.PositiveSmallIntegerField(verbose_name='Lane Number')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
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
            name='HistoricalServer',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('server_name', models.CharField(max_length=50, verbose_name='Server Name')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
                'verbose_name': 'historical server',
            },
        ),
        migrations.CreateModel(
            name='HistoricalServerFileInstance',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('filename', models.CharField(max_length=500, verbose_name='Filename')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
            ],
            options={
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
                'verbose_name': 'historical server file instance',
            },
        ),
        migrations.CreateModel(
            name='PairedFastqFiles',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dna_sequences', models.ManyToManyField(to='tantalus.DNASequences', verbose_name='Sequences')),
            ],
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
                ('created', models.DateField(verbose_name='Created')),
            ],
        ),
        migrations.CreateModel(
            name='SequenceLane',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sequencing_centre', models.CharField(max_length=50, verbose_name='Sequencing Centre')),
                ('flowcell_id', models.CharField(max_length=50, verbose_name='FlowCell ID')),
                ('lane_number', models.PositiveSmallIntegerField(verbose_name='Lane Number')),
                ('dna_library', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tantalus.DNALibrary')),
            ],
        ),
        migrations.CreateModel(
            name='Server',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('server_name', models.CharField(max_length=50, verbose_name='Server Name')),
            ],
        ),
        migrations.CreateModel(
            name='ServerFileInstance',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('filename', models.CharField(max_length=500, verbose_name='Filename')),
                ('file_resource', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tantalus.SequenceDataFile')),
                ('server', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tantalus.Server')),
            ],
        ),
        migrations.CreateModel(
            name='Transfer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='Name')),
                ('state', models.CharField(max_length=50, null=True, verbose_name='State')),
                ('result', models.IntegerField(null=True, verbose_name='Result')),
            ],
        ),
        migrations.AddField(
            model_name='pairedfastqfiles',
            name='lanes',
            field=models.ManyToManyField(to='tantalus.SequenceLane', verbose_name='Lanes'),
        ),
        migrations.AddField(
            model_name='pairedfastqfiles',
            name='reads_1_file',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reads_1_file', to='tantalus.SequenceDataFile'),
        ),
        migrations.AddField(
            model_name='pairedfastqfiles',
            name='reads_2_file',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reads_2_file', to='tantalus.SequenceDataFile'),
        ),
        migrations.AddField(
            model_name='historicalserverfileinstance',
            name='file_resource',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='tantalus.SequenceDataFile'),
        ),
        migrations.AddField(
            model_name='historicalserverfileinstance',
            name='history_user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='historicalserverfileinstance',
            name='server',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='tantalus.Server'),
        ),
        migrations.AddField(
            model_name='historicalpairedfastqfiles',
            name='reads_1_file',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='tantalus.SequenceDataFile'),
        ),
        migrations.AddField(
            model_name='historicalpairedfastqfiles',
            name='reads_2_file',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='tantalus.SequenceDataFile'),
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
            model_name='historicalazureblobfileinstance',
            name='file_resource',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='tantalus.SequenceDataFile'),
        ),
        migrations.AddField(
            model_name='historicalazureblobfileinstance',
            name='history_user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='dnasequences',
            name='sample',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tantalus.Sample'),
        ),
        migrations.AddField(
            model_name='bamfile',
            name='bam_file',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bam_file', to='tantalus.SequenceDataFile'),
        ),
        migrations.AddField(
            model_name='bamfile',
            name='bam_index_file',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bam_index_file', to='tantalus.SequenceDataFile'),
        ),
        migrations.AddField(
            model_name='bamfile',
            name='dna_sequences',
            field=models.ManyToManyField(to='tantalus.DNASequences', verbose_name='Sequences'),
        ),
        migrations.AddField(
            model_name='bamfile',
            name='lanes',
            field=models.ManyToManyField(to='tantalus.SequenceLane', verbose_name='Lanes'),
        ),
        migrations.AddField(
            model_name='azureblobfileinstance',
            name='file_resource',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tantalus.SequenceDataFile'),
        ),
    ]
