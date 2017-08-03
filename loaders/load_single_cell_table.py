import os
import sys
import pandas as pd
import django

sys.path.append('./')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tantalus.settings')
django.setup()

import tantalus.models

data = pd.HDFStore('loaders/single_cell_hiseq_fastq_metadata.h5', 'r')['/metadata']

server = tantalus.models.Server()
server.name = 'rocks'
server.save()

for idx in data.index:
    reads_files = []

    for read_end in ('1', '2'):
        fastq_filename = data.loc[idx, 'read' + read_end]

        seqfile = tantalus.models.SequenceDataFile()
        seqfile.md5 = data.loc[idx, 'md5' + read_end]
        seqfile.size = data.loc[idx, 'size' + read_end]
        seqfile.created = pd.Timestamp(data.loc[idx, 'create' + read_end], tz='Canada/Pacific')
        seqfile.save()

        reads_files.append(seqfile)

        serverfile = tantalus.models.ServerFileInstance()
        serverfile.server = server
        serverfile.file_resource = seqfile
        serverfile.filename = fastq_filename
        serverfile.save()

    fastq_files = tantalus.models.PairedFastqFiles()
    fastq_files.reads_1_file = seqfile
    fastq_files.reads_2_file = seqfile
    fastq_files.save()

