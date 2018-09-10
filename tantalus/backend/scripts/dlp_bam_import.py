import argparse
import os
import sys
import datetime
import time
import pysam
import json
import azure.storage.blob
import pandas as pd
from django.core.serializers.json import DjangoJSONEncoder
from tantalus.backend.colossus import *
from tantalus.backend.dlp import *

def get_bam_ref_genome(bam_header):
    for pg in bam_header['PG']:
        if 'bwa' in pg['ID']:
            if 'GRCh37-lite.fa' in pg['CL']:
                return 'grch37'
            if 'mm10' in pg['CL']:
                return 'mm10'

    raise Exception('no ref genome found')


def get_bam_aligner_name(bam_header):
    for pg in bam_header['PG']:
        if 'bwa' in pg['ID']:
            if 'sampe' in pg['CL']:
                return 'bwa_aln'
            if 'mem' in pg['CL']:
                return 'bwa_mem'

    raise Exception('no aligner name found')


def query_colossus_dlp_index_info(library_id):
    sublibraries = get_colossus_sublibraries_from_library_id(library_id)

    cell_indices = {}
    for sublib in sublibraries:
        sample_id = sublib['sample_id']['sample_id']
        row = 'R{:02}'.format(sublib['row'])
        col = 'C{:02}'.format(sublib['column'])
        cell_id = '-'.join([sample_id, library_id, row, col])
        index_sequence = sublib['primer_i7'] + '-' + sublib['primer_i5']
        cell_indices[cell_id] = index_sequence

    return cell_indices


def get_bam_header_file(filename):
    return pysam.AlignmentFile(filename).header


def get_bam_header_blob(blob_service, container_name, blob_name):
    sas_token = blob_service.generate_blob_shared_access_signature(
        container_name, blob_name,
        permission=azure.storage.blob.BlobPermissions.READ,
        expiry=datetime.datetime.utcnow() + datetime.timedelta(hours=1))

    blob_url = blob_service.make_blob_url(
        container_name=container_name,
        blob_name=blob_name,
        protocol='http',
        sas_token=sas_token)

    return pysam.AlignmentFile(blob_url).header


def get_bam_header_info(header):
    index_info = {}

    sample_ids = set()
    library_ids = set()
    index_sequences = set()
    sequence_lanes = list()

    for read_group in header['RG']:
        cell_id = read_group['SM']
        flowcell_lane = read_group['PU']
        sample_id, library_id, row, col = cell_id.split('-')

        if library_id not in index_info:
            index_info[library_id] = query_colossus_dlp_index_info(library_id)

        index_sequence = index_info[library_id][cell_id]

        flowcell_id = flowcell_lane.split('_')[0]
        lane_number = ''
        if '_' in flowcell_lane:
            lane_number = flowcell_lane.split('_')[1]

        sequence_lane = dict(
            flowcell_id=flowcell_id,
            lane_number=lane_number,
        )

        sample_ids.add(sample_id)
        library_ids.add(library_id)
        index_sequences.add(index_sequence)
        sequence_lanes.append(sequence_lane)

    if len(sample_ids) > 1:
        raise Exception('multiple sample ids {}'.format(sample_ids))

    if len(library_ids) > 1:
        raise Exception('multiple library ids {}'.format(library_ids))

    if len(index_sequences) > 1:
        raise Exception('multiple index_sequences {}'.format(index_sequences))

    return {
        'sample_id': sample_ids.pop(),
        'library_id': library_ids.pop(),
        'index_sequence': index_sequences.pop(),
        'sequence_lanes': sequence_lanes,
    }


def get_size_file(filename):
    return os.path.getsize(filename)


def get_created_time_file(filename):
    return pd.Timestamp(time.ctime(os.path.getmtime(filename)), tz='Canada/Pacific')


def get_size_blob(blob_service, container, blobname):
    properties = blob_service.get_blob_properties(container, blobname)
    blobsize = properties.properties.content_length
    return blobsize


def get_created_time_blob(blob_service, container, blobname):
    properties = blob_service.get_blob_properties(container, blobname)
    created_time = properties.properties.last_modified.isoformat()
    return created_time


def import_dlp_realign_bams(json_filename, storage_name, storage_type, bam_filenames, **kwargs):
    metadata = []

    if storage_type == 'blob':
        for bam_filename in bam_filenames:
            metadata.extend(import_dlp_realign_bam_blob(bam_filename, kwargs['blob_container_name']))
    elif storage_type == 'server':
        for bam_filename in bam_filenames:
            metadata.extend(import_dlp_realign_bam_server(bam_filename))
    else:
        raise ValueError('unsupported storage type {}'.format(storage_type))

    json_list = tantalus.backend.dlp.create_sequence_dataset_models(metadata, storage_name)

    with open(json_filename, 'w') as f:
        json.dump(json_list, f, indent=4, sort_keys=True, cls=DjangoJSONEncoder)


def import_dlp_realign_bam_blob(bam_filename, container_name):
    # Assumption: bam filename is prefixed by container name
    bam_filename = bam_filename.strip('/')
    if not bam_filename.startswith(container_name + '/'):
        raise Exception('expected container name {} as prefix for bam filename {}'.format(
            container_name, bam_filename))
    bam_filename = bam_filename[len(container_name + '/'):]

    bai_filename = bam_filename + '.bai'

    blob_service = azure.storage.blob.BlockBlobService(
        account_name=os.environ['AZURE_STORAGE_ACCOUNT'],
        account_key=os.environ['AZURE_STORAGE_KEY'])

    bam_header = get_bam_header_blob(blob_service, container_name, bam_filename)

    bam_info = {
        'filename': bam_filename,
        'size': get_size_blob(blob_service, container_name, bam_filename),
        'created': get_created_time_blob(blob_service, container_name, bam_filename),
        'file_type': 'BAM',
    }

    bai_info = {
        'filename': bai_filename,
        'size': get_size_blob(blob_service, container_name, bai_filename),
        'created': get_created_time_blob(blob_service, container_name, bai_filename),
        'file_type': 'BAI',
    }

    return [
        create_file_metadata(bam_info, bam_header),
        create_file_metadata(bai_info, bam_header),
    ]


def import_dlp_realign_bam_server(bam_filename):
    bai_filename = bam_filename + '.bai'

    bam_header = get_bam_header_file(bam_filename)

    bam_info = {
        'filename': bam_filename,
        'size': get_size_file(bam_filename),
        'created': get_created_time_file(bam_filename),
        'file_type': 'BAM',
    }

    bai_info = {
        'filename': bai_filename,
        'size': get_size_file(bai_filename),
        'created': get_created_time_file(bai_filename),
        'file_type': 'BAI',
    }

    return [
        create_file_metadata(bam_info, bam_header),
        create_file_metadata(bai_info, bam_header),
    ]


def create_file_metadata(file_info, bam_header):
    ref_genome = get_bam_ref_genome(bam_header)
    aligner_name = get_bam_aligner_name(bam_header)
    bam_header_info = get_bam_header_info(bam_header)

    return dict(
        dataset_type='BAM',
        sample_id=bam_header_info['sample_id'],
        library_id=bam_header_info['library_id'],
        library_type='SC_WGS',
        index_format='D',
        sequence_lanes=bam_header_info['sequence_lanes'],
        ref_genome=ref_genome,
        aligner_name=aligner_name,
        file_type=file_info['file_type'],
        size=file_info['size'],
        created=file_info['created'],
        index_sequence=bam_header_info['index_sequence'],
        compression='UNCOMPRESSED',
        filename=file_info['filename'],
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('json_data')
    parser.add_argument('storage_name')
    parser.add_argument('storage_type', choices=['blob', 'server'])
    parser.add_argument('bam_filenames', nargs='+')
    parser.add_argument('--blob_container_name', required=False)
    parser.add_argument('--server_storage_directory', required=False)
    args = vars(parser.parse_args())

    json_list = import_dlp_realign_bams(
        args['json_data'],
        args['storage_name'],
        args['storage_type'],
        args['bam_filenames'],
        server_storage_directory=args.get('server_storage_directory'),
        blob_container_name=args.get('blob_container_name'))

