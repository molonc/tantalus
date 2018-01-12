import os
import sys
import string
import pandas as pd
import django


sys.path.append('./')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tantalus.settings')
django.setup()

import tantalus.models

#TODO: need to test for bugs still

def reverse_complement(sequence):
    return sequence[::-1].translate(string.maketrans('ACTGactg','TGACtgac'))


def get_libraries_in_data():
    libraries = pd.HDFStore('loaders/single_cell_hiseq_fastq_metadata.h5', 'r')['/metadata']['id']
    return libraries


def load_library_and_get_data(gsc_library_id):
    data = pd.HDFStore('loaders/single_cell_hiseq_fastq_metadata.h5', 'r')['/metadata']
    data = data[data['id'] == gsc_library_id]
    return data


def create_reads_file(data, in_storage, directory_to_strip):
    for idx in data.index:
        reads_files = {}

        with django.db.transaction.atomic():
            for read_end in ('1', '2'):
                fastq_filename = data.loc[idx, 'read' + read_end]
                relative_filename = fastq_filename.replace(directory_to_strip, "")

                file_resource = tantalus.models.FileResource.objects.get_or_create(
                    md5=data.loc[idx, 'md5' + read_end],
                    size=data.loc[idx, 'size' + read_end],
                    created=pd.Timestamp(data.loc[idx, 'create' + read_end], tz='Canada/Pacific'),
                    file_type=tantalus.models.FileResource.FQ,
                    read_end=int(read_end),
                    compression=tantalus.models.FileResource.GZIP,
                    filename=relative_filename
                )[0]

                reads_files[read_end] = file_resource

                tantalus.models.FileInstance.objects.get_or_create(
                    storage=in_storage,
                    file_resource=file_resource
                )

            fastq_dna_sequences = tantalus.models.DNASequences.objects.filter(index_sequence=reverse_complement(data.loc[idx, 'code1']) + '-' + data.loc[idx, 'code2'])
            # assert len(fastq_dna_sequences) == 1
            if len(fastq_dna_sequences) == 0:
                print("WARNING. Cannot find sequence {} for library {}".format(reverse_complement(data.loc[idx, 'code1']) + '-' + data.loc[idx, 'code2'], data.loc[idx, 'id']))
                continue

            paired_end_fastq, pefq_created = tantalus.models.PairedEndFastqFiles.objects.get_or_create(
                reads_1_file=reads_files['1'],
                reads_2_file=reads_files['2'],
                dna_sequences=fastq_dna_sequences[0],
            )
            if pefq_created:
                paired_end_fastq[0].lanes = tantalus.models.SequenceLane.objects.filter(flowcell_id=data.loc[idx, 'flowcell'],
                                                                                lane_number=data.loc[idx, 'lane'])


if __name__ == '__main__':
    sequencing_library_ids = tantalus.models.SequenceLane.objects.all().values_list('sequencing_library_id', flat=True)
    gsc_library_ids = get_libraries_in_data()
    storage = tantalus.models.Storage.objects.get(name="rocks")
    for lib_id in gsc_library_ids.unique():
        data = load_library_and_get_data(lib_id)
        create_reads_file(data, storage, storage.storage_directory)
