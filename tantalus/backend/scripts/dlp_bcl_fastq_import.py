import argparse
import hashlib
import collections
import django
import time
import os
import re
import json
import pandas as pd
from django.core.serializers.json import DjangoJSONEncoder

from tantalus.backend.colossus import *


# Hard coded BRC details
BRC_INSTRUMENT = "NextSeq550"
BRC_INDEX_FORMAT = "D"
BRC_LIBRARY_TYPE = 'SINGLE_CELL_WGS'
BRC_READ_TYPE = 'PAIRED'
BRC_SEQ_CENTRE = 'BRC'


def query_colossus_dlp_cell_info(library_id):

    sublibraries = get_colossus_sublibraries_from_library_id(library_id)

    row_column_map = {}
    for sublib in sublibraries:
        index_sequence = sublib['primer_i7'] + '-' + sublib['primer_i5']
        row_column_map[(sublib['row'], sublib['column'])] = {
            'index_sequence': index_sequence,
            'sample_id': sublib['sample_id']['sample_id'],
        }

    return row_column_map


def load_brc_fastqs(json_filename, flowcell_id, storage_name, storage_directory, output_dir):
    # Check for .. in file path
    if ".." in output_dir:
        raise Exception("Invalid path for output_dir. \'..\' detected")

    # Check that output_dir is actually in storage
    if not output_dir.startswith(storage_directory):
        raise Exception("Invalid path for output_dir. {} doesn't seem to be in the specified storage".format(output_dir))

    # Check that path is valid.
    if not os.path.isdir(output_dir):
        raise Exception("output directory {} not a directory".format(output_dir))

    fastq_info = get_fastq_info(output_dir)

    json_list = create_models(fastq_info, flowcell_id, storage_name, storage_directory)

    with open(json_filename, 'w') as f:
        json.dump(json_list, f, indent=4, sort_keys=True, cls=DjangoJSONEncoder)


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
        raise Exception("no fastq files in output directory {}".format(output_dir))

    # Cell info keyed by dlp library id
    cell_info = {}

    # Fastq filenames and info keyed by fastq id, read end
    fastq_info = {}

    for filename in fastq_filenames:
        match = re.match("^([a-zA-Z0-9]+)-([a-zA-Z0-9]+)-R(\\d+)-C(\\d+)_S(\\d+)(_L(\\d+))?_R([12])_001.fastq.gz$", filename)

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


def create_models(fastq_info, flowcell_id, storage_name, storage_directory):
    """ Create models for paired fastqs.
    """

    storage = dict(
        name=storage_name,
    )

    json_list = []

    for fastq_id, info in fastq_info.iteritems():
        sample = dict(
            sample_id=info['sample_id'],
        )

        dna_library = dict(
            library_id=info['library_id'],
            index_format=BRC_INDEX_FORMAT,
            library_type=BRC_LIBRARY_TYPE,
        )

        sequence_lane = dict(
            flowcell_id=flowcell_id,
            lane_number=info['lane_number'],
            read_type=BRC_READ_TYPE,
            sequencing_centre=BRC_SEQ_CENTRE,
            sequencing_instrument=BRC_INSTRUMENT,
        )

        read_group = dict(
            sample=sample,
            dna_library=dna_library,
            index_sequence=info['index_sequence'],
            sequence_lane=sequence_lane,
            sequencing_library_id=info['library_id'],
        )

        read_end_file_resources = {}

        for read_end, filepath in info['filepaths'].iteritems():
            if not filepath.startswith(storage_directory):
                raise Exception('file {} expected in directory {}'.format(
                    filepath, storage_directory))
            filename = filepath.replace(storage_directory, '')
            filename = filename.lstrip('/')

            file_resource = dict(
                size=os.path.getsize(filepath),
                created=pd.Timestamp(time.ctime(os.path.getmtime(filepath)), tz='Canada/Pacific'),
                file_type='FQ',
                read_end=read_end,
                compression='GZIP',
                filename=filename,
            )

            file_instance = dict(
                storage=storage,
                file_resource=file_resource,
                filename_override='',
                model='FileInstance',
            )

            json_list.append(file_instance)

            read_end_file_resources[read_end] = file_resource

        fastq_dataset = dict(
            reads_1_file=read_end_file_resources[1],
            reads_2_file=read_end_file_resources[2],
            read_groups=[read_group],
            model='PairedEndFastqFiles',
        )

        json_list.append(fastq_dataset)

    return json_list


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('json_data')
    parser.add_argument('flowcell_id')
    parser.add_argument('storage_name')
    parser.add_argument('storage_directory')
    parser.add_argument('output_dir')
    args = vars(parser.parse_args())

    load_brc_fastqs(
        args['json_data'], args['flowcell_id'],
        args['storage_name'], args['storage_directory'],
        args['output_dir'])

