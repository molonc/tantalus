import os
import sys
import string
import pandas as pd
import django


sys.path.append('./')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tantalus.settings')
django.setup()
DIRECTORY_TO_STRIP = "/share/lustre/archive/single_cell_indexing/HiSeq/"

import tantalus.models

def reverse_complement(sequence):
    return sequence[::-1].translate(string.maketrans('ACTGactg','TGACtgac'))


def load_library_and_get_data(gsc_library_id):
    data = pd.HDFStore('loaders/single_cell_hiseq_fastq_metadata.h5', 'r')['/metadata']
    data = data[data['id'] == gsc_library_id]
    return data


def create_reads_file(data, in_storage, directory_to_strip=DIRECTORY_TO_STRIP):
    for idx in data.index:
        reads_files = {}

        for read_end in ('1', '2'):
            fastq_filename = data.loc[idx, 'read' + read_end]

            file_resource = tantalus.models.FileResource()
            file_resource.md5 = data.loc[idx, 'md5' + read_end]
            file_resource.size = data.loc[idx, 'size' + read_end]
            file_resource.created = pd.Timestamp(data.loc[idx, 'create' + read_end], tz='Canada/Pacific')
            file_resource.file_type = tantalus.models.FileResource.FQ
            file_resource.read_end = int(read_end)
            file_resource.compression = tantalus.models.FileResource.GZIP

            relative_filename = fastq_filename.replace(directory_to_strip, "")
            file_resource.filename = relative_filename
            # print file_resource.filename

            file_resource.save()

            reads_files[read_end] = file_resource

            serverfile = tantalus.models.FileInstance()
            serverfile.storage = in_storage
            serverfile.file_resource = file_resource
            serverfile.full_clean()
            serverfile.save()

        fastq_dna_sequences = tantalus.models.DNASequences.objects.filter(index_sequence=reverse_complement(data.loc[idx, 'code1']) + '-' + data.loc[idx, 'code2'])
        assert len(fastq_dna_sequences) == 1

        fastq_files = tantalus.models.PairedEndFastqFiles()
        fastq_files.reads_1_file = reads_files['1']
        fastq_files.reads_2_file = reads_files['2']
        fastq_files.dna_sequences = fastq_dna_sequences[0]
        fastq_files.save()
        fastq_files.lanes = tantalus.models.SequenceLane.objects.filter(flowcell_id=data.loc[idx, 'flowcell'], lane_number=data.loc[idx, 'lane'])
        fastq_files.full_clean()
        fastq_files.save()

        reads_files['1'].full_clean()
        reads_files['2'].full_clean()
        reads_files['1'].save()
        reads_files['2'].save()

if __name__ == '__main__':

    tantalus.models.ServerStorage.objects.all().delete()
    tantalus.models.AzureBlobStorage.objects.all().delete()
    tantalus.models.FileResource.objects.all().delete()
    tantalus.models.FileInstance.objects.all().delete()
    tantalus.models.PairedEndFastqFiles.objects.all().delete()

    storage = tantalus.models.ServerStorage()
    storage.name = 'rocks'
    storage.server_ip = 'rocks3.cluster.bccrc.ca'
    storage.storage_directory = '/share/lustre/amcpherson/tantalus_test'
    storage.username = 'amcpherson'
    storage.full_clean()
    storage.save()

    storage = tantalus.models.ServerStorage()
    storage.name = 'gsc'
    storage.server_ip = '10.9.208.161'
    storage.storage_directory = '/'
    storage.username = 'amcpherson'
    storage.full_clean()
    storage.save()

    storage = tantalus.models.ServerStorage()
    storage.name = 'shahlab'
    storage.server_ip = '10.9.208.161'
    storage.storage_directory = '/shahlab/amcpherson/tantalus_test'
    storage.username = 'amcpherson'
    storage.full_clean()
    storage.save()

    blob_storage = tantalus.models.AzureBlobStorage()
    blob_storage.name = 'azure_sc_fastqs'
    blob_storage.storage_account = 'singlecellstorage'
    blob_storage.storage_container = 'fastqs'
    blob_storage.storage_key = 'okQAsp72BagVWpGLEaUNO30jH9XGLuVj3EDmbtg7oV6nmH7+9E+4csF+AXn4G3YMEKebnCnsRwVu9fRhh2RiMQ=='
    blob_storage.full_clean()
    blob_storage.save()

    data = load_library_and_get_data('PX0593')

    create_reads_file(data, storage)
