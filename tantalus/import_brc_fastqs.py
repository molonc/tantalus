import hashlib

import collections
import django
import time
import os

import re

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tantalus.settings')
    django.setup()

import pandas as pd
import requests

import tantalus.models
import tantalus.tasks

# Hard coded BRC details
BRC_INSTRUMENT = "NextSeq550"
BRC_INDEX_FORMAT = "D"
BRC_LIBRARY_TYPE = tantalus.models.DNALibrary.SINGLE_CELL_WGS
BRC_READ_TYPE = tantalus.models.SequenceLane.PAIRED
BRC_SEQ_CENTRE = tantalus.models.SequenceLane.BRC


def create_sample(sample_id):
    sample, created = tantalus.models.Sample.objects.get_or_create(
        sample_id=sample_id,
    )
    if created:
        sample.save()
    return sample


def create_dna_library(library_id):
    dna_library, created = tantalus.models.DNALibrary.objects.get_or_create(
        library_id=library_id,
        index_format=BRC_INDEX_FORMAT,
        library_type=BRC_LIBRARY_TYPE,
    )
    if created:
        dna_library.save()
    return dna_library


def create_sequence_lane(dna_library, flowcell_id, lane_number, sequencing_library_id):
    sequence_lane, created = tantalus.models.SequenceLane.objects.get_or_create(
        dna_library=dna_library,
        flowcell_id=flowcell_id,
        lane_number=lane_number,
        read_type=BRC_READ_TYPE,
        sequencing_centre=BRC_SEQ_CENTRE,
        sequencing_instrument=BRC_INSTRUMENT,
        sequencing_library_id=sequencing_library_id,
    )
    if created:
        sequence_lane.save()
    return sequence_lane


def create_dna_sequences(dna_library, sample, index_sequence):
    dna_sequence, created = tantalus.models.DNASequences.objects.get_or_create(
        dna_library=dna_library,
        sample=sample,
        index_sequence=index_sequence,
    )
    if created:
        dna_sequence.save()
    return dna_sequence


def create_file_resource(filename, filepath, read_end):
    file_resource_fields = {
        'size': os.path.getsize(filepath),
        'file_type': tantalus.models.FileResource.FQ,
        'read_end': read_end,
        'compression': tantalus.models.FileResource.GZIP,
        'filename': filename,
    }
    created_time = pd.Timestamp(time.ctime(os.path.getmtime(filepath)), tz='Canada/Pacific')
    # Get existing file resource and update created time or
    # create a new file resource
    try:
        file_resource = tantalus.models.FileResource.objects.get(
            **file_resource_fields)
        file_resource.created = created_time
        file_resource.save()
        return file_resource
    except tantalus.models.FileResource.DoesNotExist:
        file_resource = tantalus.models.FileResource.objects.create(
            created=created_time,
            **file_resource_fields)
        return file_resource


def create_file_instance(storage, file_resource):
    file_instance, created = tantalus.models.FileInstance.objects.get_or_create(
        storage=storage,
        file_resource=file_resource,
        filename_override='',
    )
    if created:
        file_instance.save()
    return file_instance, created


def create_paired_end_fastq_files(reads_1_file, reads_2_file, dna_sequence, lane):
    Paired_End_Fastq_Files, created = tantalus.models.PairedEndFastqFiles.objects.get_or_create(
        reads_1_file=reads_1_file,
        reads_2_file=reads_2_file,
        dna_sequences=dna_sequence,
    )
    if created:
        Paired_End_Fastq_Files.save()
    Paired_End_Fastq_Files.lanes.add(lane)
    Paired_End_Fastq_Files.save()


def query_colossus_dlp_cell_info(library_id):
    library_url = '{}library/?pool_id={}'.format(
        'http://colossus.bcgsc.ca/api/',#django.conf.settings.COLOSSUS_API_URL,
        library_id)

    r = requests.get(library_url)

    if r.status_code != 200:
        raise Exception('Returned {}: {}'.format(r.status_code, r.reason))

    if len(r.json()['results']) == 0:
        raise Exception('No entries for library {}'.format(library_id))

    if len(r.json()['results']) > 1:
        raise Exception('Multiple entries for library {}'.format(library_id))

    data = r.json()[0]

    row_column_map = {}
    for sublib in data['sublibraryinformation_set']:
        index_sequence = sublib['primer_i7'] + '-' + sublib['primer_i5']
        row_column_map[(sublib['row'], sublib['column'])] = {
            'index_sequence': index_sequence,
            'sample_id': sublib['sample_id']['sample_id'],
        }

    return row_column_map


#### output_dir = '/genesis/shahlab/archive/single_cell_indexing/NextSeq/fastq/171031_NS500668_0271_AHLNK5AFXX/'

def load_brc_fastqs(import_brc_fastqs):
    # Check for .. in file path
    if ".." in import_brc_fastqs.output_dir:
        raise Exception("Invalid path for output_dir. \'..\' detected")

    # Check that output_dir is actually in storage
    if not import_brc_fastqs.output_dir.startswith(import_brc_fastqs.storage.get_storage_directory()):
        raise Exception("Invalid path for output_dir. {} doesn't seem to be in the specified storage".format(import_brc_fastqs.output_dir))

    # Check that path is valid.
    if not os.path.isdir(import_brc_fastqs.output_dir):
        raise Exception("output directory {} not a directory".format(import_brc_fastqs.output_dir))

    fastq_info = get_fastq_info(import_brc_fastqs.output_dir)

    create_models(fastq_info, import_brc_fastqs.flowcell_id, import_brc_fastqs.storage)


def _update_info(info, key, value):
    if key in info:
        if info[key] != value:
            raise ValueError('{} different from {}'.format(info[key], value))
    else:
        info[key] = value


def get_fastq_info(output_dir):
    """ Retrieve fastq filenames and metadata from output directory.
    """
    fastq_filenames = os.listdir(output_dir)

    # Filter for gzipped fastq files
    fastq_filenames = filter(lambda x: ".fastq.gz" in x, fastq_filenames)

    # Remove undetermined fastqs
    fastq_filenames = filter(lambda x: "Undetermined" not in x, fastq_filenames)

    # Check that the path actually has fastq files
    if len(fastq_filenames) == 0:
        raise Exception("no fastq files in output directory {}".format(import_brc_fastqs.output_dir))

    # Cell info keyed by dlp library id
    cell_info = {}

    # Fastq filenames and info keyed by fastq id, read end
    fastq_info = {}

    for filename in fastq_filenames:
        match = re.match("^([a-zA-Z0-9]+)-(A[a-zA-Z0-9]+)-R(\\d+)-C(\\d+)_S(\\d+)(_L(\\d+))?_R([12])_001.fastq.gz$", filename)

        if match is None:
            raise Exception('unrecognized fastq filename structure for {}'.format(filename))

        filename_fields = match.groups()

        primary_sample_id = filename_fields[0]
        library_id = filename_fields[1]
        row = int(filename_fields[2])
        column = int(filename_fields[3])
        lane_number = filename_fields[6]
        if lane_number is not None:
            lane_number = int(lane_number)
        read_end = int(filename_fields[7])

        if library_id not in cell_info:
            cell_info[library_id] = query_colossus_dlp_cell_info(library_id)

        index_sequence = cell_info[library_id][row, column]['index_sequence']
        sample_id = cell_info[library_id][row, column]['sample_id']

        fastq_id = (primary_sample_id, library_id, row, column, lane_number)

        if fastq_id not in fastq_info:
            fastq_info[fastq_id] = {}
            fastq_info[fastq_id]['filepaths'] = {}

        if read_end in fastq_info[fastq_id]['filepaths']:
            raise Exception('found duplicate for filename {}'.format(filename))

        fastq_info[fastq_id]['filepaths'][read_end] = os.path.join(output_dir, filename)

        try:
            _update_info(fastq_info[fastq_id], 'library_id', library_id)
            _update_info(fastq_info[fastq_id], 'lane_number', lane_number)
            _update_info(fastq_info[fastq_id], 'index_sequence', index_sequence)
            _update_info(fastq_info[fastq_id], 'sample_id', sample_id)
        except ValueError as e:
            raise Exception('file {} has different metadata from matching pair: ' + str(e))

    return fastq_info


def create_models(fastq_info, flowcell_id, storage):
    """ Create models for paired fastqs.
    """

    storage_directory = storage.get_storage_directory()

    if not storage_directory.endswith('/'):
        storage_directory = storage_directory + '/'

    with django.db.transaction.atomic():
        new_file_instances = []

        for fastq_id, info in fastq_info.iteritems():
            sample = create_sample(
                sample_id=info['sample_id'])

            dna_library = create_dna_library(
                library_id=info['library_id'])

            sequence_lane = create_sequence_lane(
                dna_library=dna_library,
                flowcell_id=flowcell_id,
                lane_number=info['lane_number'],
                sequencing_library_id=info['library_id'],
            )

            dna_sequences = create_dna_sequences(
                dna_library=dna_library,
                sample=sample,
                index_sequence=info['index_sequence'],
            )

            read_end_file_resources = {}

            for read_end, filepath in info['filepaths'].iteritems():
                if not filepath.startswith(storage_directory):
                    raise Exception('file {} expected in directory {}'.format(
                        filepath, storage_directory))
                filename = filepath.replace(storage_directory, '')

                file_resource = create_file_resource(
                    filename=filename,
                    filepath=filepath,
                    read_end=read_end,
                )

                file_instance, created = create_file_instance(
                    storage=storage,
                    file_resource=file_resource,
                )
                if created:
                    new_file_instances.append(file_instance)

                read_end_file_resources[read_end] = file_resource

            create_paired_end_fastq_files(
                reads_1_file=read_end_file_resources[1],
                reads_2_file=read_end_file_resources[2],
                dna_sequence=dna_sequences,
                lane=sequence_lane,
            )

        django.db.transaction.on_commit(lambda: tantalus.utils.start_md5_checks(new_file_instances))


# Testing code, remove later
if __name__ == "__main__":
    storage, created = tantalus.models.ServerStorage.objects.get_or_create(
        name='test',
        server_ip='localhost',
        storage_directory='/Users/amcphers/Scratch/tantalus_test',
        username='test',
        queue_prefix='test',
    )

    if created:
        storage.save()

    import_brc_fastqs, created  = tantalus.models.BRCFastqImport.objects.get_or_create(
        output_dir='/Users/amcphers/Scratch/tantalus_test/output',
        storage=tantalus.models.ServerStorage.objects.get(name='test'),
        flowcell_id='AHKNYTAFXX',
    )

    if created:
        storage.save()

    load_brc_fastqs(import_brc_fastqs)
