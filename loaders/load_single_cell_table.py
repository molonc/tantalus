import os
import sys
import pandas as pd
import django

sys.path.append('./')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tantalus.settings')
django.setup()

import tantalus.models

data = pd.HDFStore('loaders/single_cell_hiseq_fastq_metadata.h5', 'r')['/metadata'].head(1000)

storage = tantalus.models.ServerStorage()
storage.name = 'rocks'
storage.server_ip = 'rocks.cluster.bccrc.ca'
storage.storage_directory = '/share/lustre/archive'
storage.save()

for idx in data.index:
    reads_files = {}

    for read_end in ('1', '2'):
        fastq_filename = data.loc[idx, 'read' + read_end]

        seqfile = tantalus.models.SequenceDataFile()
        seqfile.md5 = data.loc[idx, 'md5' + read_end]
        seqfile.size = data.loc[idx, 'size' + read_end]
        seqfile.created = pd.Timestamp(data.loc[idx, 'create' + read_end], tz='Canada/Pacific')
        seqfile.file_type = 'FQ'
        seqfile.save()

        reads_files[read_end] = seqfile

        serverfile = tantalus.models.FileInstance()
        serverfile.storage = storage
        serverfile.file_resource = seqfile
        serverfile.filename = fastq_filename
        serverfile.save()

    fastq_files = tantalus.models.PairedEndFastqFiles()
    fastq_files.reads_1_file = reads_files['1']
    fastq_files.reads_2_file = reads_files['2']
    fastq_files.save()
    fastq_files.sequence_data.add(reads_files['1'])
    fastq_files.sequence_data.add(reads_files['2'])
    fastq_files.save()



