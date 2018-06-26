import json
import os
import requests
import time
import argparse
import pandas as pd
from datetime import datetime
from django.core.serializers.json import DjangoJSONEncoder

import tantalus.backend.gsc


def convert_time(a):
    try:
        return datetime.strptime(a, '%Y-%m-%dT%H:%M:%S')
    except:
        pass
    try:
        return datetime.strptime(a, '%Y-%m-%dT%H:%M:%S.%f')
    except:
        pass
    raise


def add_compression_suffix(path, compression):
    # GSC paths for non-lane SpEC-compressed BAM files. Differ from BAM
    # paths above only in that they have `.spec` attached on the end
    if compression == 'spec':
        return path + '.spec'
    else:
        raise ValueError('unsupported compression {}'.format(compression))

merge_bam_path_template = {
    'WGS': '{data_path}/{library_name}_{num_lanes}_lane{lane_pluralize}_dupsFlagged.bam',
    'EXOME': '{data_path}/{library_name}_{num_lanes}_lane{lane_pluralize}_dupsFlagged.bam',
}

def get_merge_bam_path(library_type, data_path, library_name, num_lanes, compression=None):
    lane_pluralize = ('', 's')[num_lanes > 1]
    bam_path = merge_bam_path_template[library_type].format(
        data_path=data_path,
        library_name=library_name,
        num_lanes=num_lanes,
        lane_pluralize=lane_pluralize)
    if compression is not None:
        bam_path = add_compression_suffix(bam_path, compression)
    return bam_path

lane_bam_path_templates = {
    'WGS': '{data_path}/{flowcell_code}_{lane_number}.bam',
    'RNASEQ': '{data_path}/{flowcell_code}_{lane_number}_withJunctionsOnGenome_dupsFlagged.bam',
}

multiplexed_lane_bam_path_templates = {
    'WGS': '{data_path}/{flowcell_code}_{lane_number}_{adapter_index_sequence}.bam',
    'RNASEQ': '{data_path}/{flowcell_code}_{lane_number}_{adapter_index_sequence}_withJunctionsOnGenome_dupsFlagged.bam',
}

def get_lane_bam_path(library_type, data_path, flowcell_code, lane_number, adapter_index_sequence=None, compression=None):
    if adapter_index_sequence is not None:
        bam_path = multiplexed_lane_bam_path_templates[library_type].format(
            data_path=data_path,
            flowcell_code=flowcell_code,
            lane_number=lane_number,
            adapter_index_sequence=adapter_index_sequence)
    else:
        bam_path = lane_bam_path_templates[library_type].format(
            data_path=data_path,
            flowcell_code=flowcell_code,
            lane_number=lane_number)
    if compression is not None:
        bam_path = add_compression_suffix(bam_path, compression)
    return bam_path

protocol_id_map = {
    12: 'WGS',
    73: 'WGS',
    136: 'WGS',
    140: 'WGS',
    123: 'WGS',
    179: 'WGS',
    96: 'EXOME',
    80: 'RNASEQ',
    137: 'RNASEQ',
}

solexa_run_type_map = {
    'Paired': 'P',
}


def add_gsc_wgs_bam_dataset(bam_path, storage, sample, library, lane_infos, is_spec=False):
    library_name = library['library_id']

    bai_path = bam_path + '.bai'

    json_list = []

    # ASSUMPTION: GSC stored files are pathed from root 
    bam_filename_override = bam_path
    bai_filename_override = bai_path

    # ASSUMPTION: meaningful path starts at library_name
    bam_filename = bam_path[bam_path.find(library_name):]
    bai_filename = bai_path[bai_path.find(library_name):]

    # Prepend sample id to filenames
    bam_filename = os.path.join(sample['sample_id'], bam_filename)
    bai_filename = os.path.join(sample['sample_id'], bai_filename)

    # Save BAM file info xor save BAM SpEC file info
    bam_file = dict(
        size=os.path.getsize(bam_path),
        created=pd.Timestamp(time.ctime(os.path.getmtime(bam_path)), tz='Canada/Pacific'),
        file_type='BAM',
        read_end=None,
        compression='SPEC' if is_spec else 'UNCOMPRESSED',
        filename=bam_filename,
    )

    bam_instance = dict(
        storage=storage,
        file_resource=bam_file,
        filename_override=bam_filename_override,
        model='FileInstance',
    )
    json_list.append(bam_instance)   

    # BAI files are only found with uncompressed BAMs (and even then not
    # always)
    if not is_spec and os.path.exists(bai_path):
        bai_file = dict(
            size=os.path.getsize(bai_path),
            created=pd.Timestamp(time.ctime(os.path.getmtime(bai_path)), tz='Canada/Pacific'),
            file_type='BAI',
            read_end=None,
            compression='UNCOMPRESSED',
            filename=bai_filename,
        )

        bai_instance = dict(
            storage=storage,
            file_resource=bai_file,
            filename_override=bai_filename_override,
            model='FileInstance',
        )
        json_list.append(bai_instance)

    else:
        bai_file = None

    # If the bam file is compressed, store the file under the BamFile's
    # bam_spec_file column. Otherwise, use the bam_file column.
    bam_dataset = dict(
        bam_file=bam_file,
        bam_index_file=bai_file,
        read_groups=[],
        model='BamFile',
    )
    json_list.append(bam_dataset)

    reference_genomes = set()
    aligners = set()

    for lane_info in lane_infos:
        lane = dict(
            flowcell_id=lane_info['flowcell_code'],
            lane_number=lane_info['lane_number'],
            sequencing_centre='GSC',
            sequencing_instrument=lane_info['sequencing_instrument'],
            read_type=lane_info['read_type'],
        )

        read_group = dict(
            sample=sample,
            dna_library=library,
            index_sequence=lane_info['adapter_index_sequence'],
            sequence_lane=lane,
            sequencing_library_id=library_name,
        )
        bam_dataset['read_groups'].append(read_group)

        reference_genomes.add(lane_info['reference_genome'])
        aligners.add(lane_info['aligner'])

    if len(reference_genomes) > 1:
        bam_dataset['reference_genome'] = 'UNUSABLE'
    elif len(reference_genomes) == 1:
        bam_dataset['reference_genome'] = list(reference_genomes)[0]
        bam_dataset['aligner'] = ', '.join(aligners)

    return json_list


def add_gsc_bam_read_groups(sample, library, lane_infos):
    json_list = []

    for lane_info in lane_infos:
        lane = dict(
            flowcell_id=lane_info['flowcell_code'],
            lane_number=lane_info['lane_number'],
            sequencing_centre='GSC',
            sequencing_instrument=lane_info['sequencing_instrument'],
            read_type=lane_info['read_type'],
        )

        read_group = dict(
            sample=sample,
            dna_library=library,
            index_sequence=lane_info['adapter_index_sequence'],
            sequence_lane=lane,
            sequencing_library_id=library['library_id'],
            model='ReadGroup',
        )

        json_list.append(read_group)

    return json_list


def query_gsc_library(json_filename, libraries, skip_file_import=False, skip_older_than=None):
    """
    Take a list of library names as input.
    """

    json_list = []

    gsc_api = tantalus.backend.gsc.GSCAPI()

    # ASSUMPTION: GSC stored files are pathed from root
    storage = dict(
        name='gsc',
    )
    # TODO: check that all GSC file instances have filename overrides 

    for library_name in libraries:
        library_infos = gsc_api.query('library?name={}'.format(library_name))

        print 'importing', library_name

        for library_info in library_infos:
            protocol_info = gsc_api.query('protocol/{}'.format(library_info['protocol_id']))

            if library_info['protocol_id'] not in protocol_id_map:
                print 'warning, protocol {}:{} not supported'.format(library_info['protocol_id'], protocol_info['extended_name'])
                continue

            library_type = protocol_id_map[library_info['protocol_id']]

            print 'found', library_type

            sample_id = library_info['external_identifier']

            sample = dict(
                sample_id=sample_id,
            )

            library_name = library_info['name']

            library = dict(
                library_id=library_name,
                library_type=library_type,
                index_format='N',
            )

            merge_infos = gsc_api.query('merge?library={}'.format(library_name))

            # Keep track of lanes that are in merged BAMs so that we
            # can exclude them from the lane specific BAMs we add to
            # the database
            merged_lanes = set()

            for merge_info in merge_infos:
                data_path = merge_info['data_path']
                num_lanes = len(merge_info['merge_xrefs'])

                if merge_info['complete'] is None:
                    print 'skipping merge with no completed date'
                    continue

                completed_date = convert_time(merge_info['complete'])

                print 'merge completed', completed_date

                if skip_older_than is not None and completed_date < skip_older_than:
                    print 'skipping old merge'
                    continue

                lane_infos = []

                for merge_xref in merge_info['merge_xrefs']:
                    libcore_id = merge_xref['object_id']

                    libcore = gsc_api.query('aligned_libcore/{}/info'.format(libcore_id))
                    flowcell_id = libcore['libcore']['run']['flowcell_id']
                    lane_number = libcore['libcore']['run']['lane_number']
                    sequencing_instrument = tantalus.backend.gsc.get_sequencing_instrument(libcore['libcore']['run']['machine'])
                    solexa_run_type = libcore['libcore']['run']['solexarun_type']
                    reference_genome = libcore['lims_genome_reference']['path']
                    aligner = libcore['analysis_software']['name']
                    flowcell_info = gsc_api.query('flowcell/{}'.format(flowcell_id))
                    flowcell_code = flowcell_info['lims_flowcell_code']
                    adapter_index_sequence = libcore['libcore']['primer']['adapter_index_sequence']

                    merged_lanes.add((flowcell_code, lane_number, adapter_index_sequence))

                    lane_info = dict(
                        flowcell_code=flowcell_code,
                        lane_number=lane_number,
                        adapter_index_sequence=adapter_index_sequence,
                        sequencing_instrument=sequencing_instrument,
                        read_type=solexa_run_type_map[solexa_run_type],
                        reference_genome=reference_genome,
                        aligner=aligner,
                    )

                    lane_infos.append(lane_info)

                if skip_file_import:
                    json_list += add_gsc_bam_read_groups(sample, library, lane_infos)

                else:
                    if data_path is None:
                        raise Exception('no data path for merge info {}'.format(merge_info['id']))

                    bam_path = get_merge_bam_path(
                        library_type=library_type,
                        data_path=data_path,
                        library_name=library_name,
                        num_lanes=num_lanes)

                    bam_spec_path = get_merge_bam_path(
                        library_type=library_type,
                        data_path=data_path,
                        library_name=library_name,
                        num_lanes=num_lanes,
                        compression='spec')

                    # Test for BAM path first, then BAM SpEC path if
                    # no BAM available
                    if os.path.exists(bam_path):
                        json_list += add_gsc_wgs_bam_dataset(bam_path, storage, sample, library, lane_infos)
                    elif os.path.exists(bam_spec_path):
                        json_list += add_gsc_wgs_bam_dataset(bam_spec_path, storage, sample, library, lane_infos, is_spec=True)
                    else:
                        raise Exception('missing merged bam file {}'.format(bam_path))


            libcores = gsc_api.query('aligned_libcore/info?library={}'.format(library_name))

            for libcore in libcores:
                created_date = convert_time(libcore['created'])

                print 'libcore created', created_date

                if skip_older_than is not None and created_date < skip_older_than:
                    print 'skipping old lane'
                    continue

                flowcell_id = libcore['libcore']['run']['flowcell_id']
                lane_number = libcore['libcore']['run']['lane_number']
                sequencing_instrument = tantalus.backend.gsc.get_sequencing_instrument(libcore['libcore']['run']['machine'])
                solexa_run_type = libcore['libcore']['run']['solexarun_type']
                reference_genome = libcore['lims_genome_reference']['path']
                aligner = libcore['analysis_software']['name']
                adapter_index_sequence = libcore['libcore']['primer']['adapter_index_sequence']
                data_path = libcore['data_path']

                flowcell_info = gsc_api.query('flowcell/{}'.format(flowcell_id))
                flowcell_code = flowcell_info['lims_flowcell_code']

                # Skip lanes that are part of merged BAMs
                if (flowcell_code, lane_number, adapter_index_sequence) in merged_lanes:
                    continue

                lane_infos = [dict(
                    flowcell_code=flowcell_code,
                    lane_number=lane_number,
                    adapter_index_sequence=adapter_index_sequence,
                    sequencing_instrument=sequencing_instrument,
                    read_type=solexa_run_type_map[solexa_run_type],
                    reference_genome=reference_genome,
                    aligner=aligner,
                )]

                if skip_file_import:
                    json_list += add_gsc_bam_read_groups(sample, library, lane_infos)

                else:
                    bam_path = get_lane_bam_path(
                        library_type=library_type,
                        data_path=data_path,
                        flowcell_code=flowcell_code,
                        lane_number=lane_number,
                        adapter_index_sequence=adapter_index_sequence)

                    bam_spec_path = get_lane_bam_path(
                        library_type=library_type,
                        data_path=data_path,
                        flowcell_code=flowcell_code,
                        lane_number=lane_number,
                        adapter_index_sequence=adapter_index_sequence,
                        compression='spec')

                    # Test for BAM path first, then BAM SpEC path if
                    # no BAM available
                    if os.path.exists(bam_path):
                        json_list += add_gsc_wgs_bam_dataset(bam_path, storage, sample, library, lane_infos)
                    elif os.path.exists(bam_spec_path):
                        json_list += add_gsc_wgs_bam_dataset(bam_spec_path, storage, sample, library, lane_infos, is_spec=True)
                    else:
                        raise Exception('missing lane bam file {}'.format(bam_path))


    with open(json_filename, 'w') as f:
        json.dump(json_list, f, indent=4, sort_keys=True, cls=DjangoJSONEncoder)


def valid_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('json_data')
    parser.add_argument('library_ids', nargs='+')
    parser.add_argument('--skip_file_import', action='store_true')
    parser.add_argument('--skip_older_than', type=valid_date, default=None)
    args = vars(parser.parse_args())

    query_gsc_library(args['json_data'], args['library_ids'],
        skip_file_import=args['skip_file_import'],
        skip_older_than=args['skip_older_than'])

