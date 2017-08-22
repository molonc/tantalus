import os
import sys
import string
import pandas as pd
import django


sys.path.append('./')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tantalus.settings')
django.setup()

import tantalus.models

tantalus.models.ServerStorage.objects.all().delete()
tantalus.models.AzureBlobStorage.objects.all().delete()
tantalus.models.SequenceDataFile.objects.all().delete()
tantalus.models.FileInstance.objects.all().delete()
tantalus.models.PairedEndFastqFiles.objects.all().delete()

def reverse_complement(sequence):
    return sequence[::-1].translate(string.maketrans('ACTGactg','TGACtgac'))

data = pd.HDFStore('loaders/single_cell_hiseq_fastq_metadata.h5', 'r')['/metadata']
data = data[data['id'] == 'PX0593']

storage = tantalus.models.ServerStorage()
storage.name = 'rocks'
storage.server_ip = 'rocks3.cluster.bccrc.ca'
storage.storage_directory = '/share/lustre/archive'
storage.username = 'jngo'
storage.full_clean()
storage.save()

blob_storage = tantalus.models.AzureBlobStorage()
blob_storage.name = 'azure_sc_fastqs'
blob_storage.storage_account = 'singlecellstorage'
blob_storage.storage_container = 'fastqs'
blob_storage.storage_key = 'okQAsp72BagVWpGLEaUNO30jH9XGLuVj3EDmbtg7oV6nmH7+9E+4csF+AXn4G3YMEKebnCnsRwVu9fRhh2RiMQ=='
blob_storage.full_clean()
blob_storage.save()

for idx in data.index:
    reads_files = {}

    for read_end in ('1', '2'):
        fastq_filename = data.loc[idx, 'read' + read_end]

        seqfile = tantalus.models.SequenceDataFile()
        seqfile.md5 = data.loc[idx, 'md5' + read_end]
        seqfile.size = data.loc[idx, 'size' + read_end]
        seqfile.created = pd.Timestamp(data.loc[idx, 'create' + read_end], tz='Canada/Pacific')
        seqfile.file_type = tantalus.models.SequenceDataFile.FQ
        seqfile.compression = tantalus.models.SequenceDataFile.GZIP
        seqfile.save()

        reads_files[read_end] = seqfile

        serverfile = tantalus.models.FileInstance()
        serverfile.storage = storage
        serverfile.file_resource = seqfile
        serverfile.filename = fastq_filename
        serverfile.save()

    fastq_dna_sequences = tantalus.models.DNASequences.objects.filter(index_sequence=reverse_complement(data.loc[idx, 'code1']) + '-' + data.loc[idx, 'code2'])
    assert len(fastq_dna_sequences) == 1

    fastq_files = tantalus.models.PairedEndFastqFiles()
    fastq_files.reads_1_file = reads_files['1']
    fastq_files.reads_2_file = reads_files['2']
    fastq_files.dna_sequences = fastq_dna_sequences[0]
    fastq_files.save()
    fastq_files.lanes = tantalus.models.SequenceLane.objects.filter(flowcell_id=data.loc[idx, 'flowcell'], lane_number=data.loc[idx, 'lane'])
    fastq_files.sequence_data.add(reads_files['1'])
    fastq_files.sequence_data.add(reads_files['2'])
    fastq_files.save()

    reads_files['1'].default_filename = fastq_files.default_reads_1_filename()
    reads_files['2'].default_filename = fastq_files.default_reads_2_filename()

    reads_files['1'].full_clean()
    reads_files['2'].full_clean()
    reads_files['1'].save()
    reads_files['2'].save()
    serverfile.full_clean()
    fastq_files.full_clean()



