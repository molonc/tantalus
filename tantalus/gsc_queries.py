import json
import os
import requests
import django
import time
import collections
import string
import pandas as pd

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tantalus.settings')
    django.setup()

import tantalus.models
import tantalus.tasks
import tantalus.utils
from tantalus.colossus import *

from pprint import pprint


GSC_API_URL = "http://sbs:8100/"


class GSCAPI(object):
    def __init__(self):
        """ Create a session object, authenticating based on the tantalus user.
        """
        self.request_handle = requests.Session()

        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'}

        create_session_url = os.path.join(GSC_API_URL, 'session')
        auth_json = {
            'username': django.conf.settings.GSC_API_USERNAME,
            'password': django.conf.settings.GSC_API_PASSWORD,}

        response = self.request_handle.post(create_session_url, json=auth_json, headers=self.headers)

        if response.status_code == 200:
            # Add the authentication token to the headers.
            token = response.json().get('token')
            self.headers.update({'X-Token': token})
        else:
            raise Exception('unable to authenticate GSC API')

    def query(self, query_string):
        """ Query the gsc api
        """
        query_url = GSC_API_URL + query_string
        result = self.request_handle.get(query_url, headers=self.headers).json()

        if 'status' in result and result['status'] == 'error':
            raise Exception(result['errors'])

        return result


bam_path_template = '{data_path}/{library_name}_{num_lanes}_lane{lane_pluralize}_dupsFlagged.bam'

lane_bam_path_template = '{data_path}/{flowcell_code}_{lane_number}_{adapter_index_sequence}.bam'


wgs_protocol_ids = (
    12,
    73,
    136,
    140,
    123,
)


solexa_run_type_map = {
    'Paired': tantalus.models.SequenceLane.PAIRED}


raw_instrument_map = {
    'HiSeq': 'HiSeq2500',
    'HiSeqX': 'HiSeqX',
    'NextSeq': 'NextSeq550',
}


def get_sequencing_instrument(machine):
    """ Sequencing instrument decode.

    Example machines are HiSeq-27 or HiSeqX-2.
    """
    raw_instrument = machine.split('-')[0]
    return raw_instrument_map[raw_instrument]


class MissingFileError(Exception):
    pass


def add_gsc_wgs_bam_dataset(bam_path, storage, sample, library, lane_infos):
    library_name = library.library_id

    bai_path = bam_path + '.bai'

    new_file_instances = []

    # ASSUMPTION: GSC stored files are pathed from root 
    bam_filename_override = bam_path
    bai_filename_override = bai_path

    # ASSUMPTION: meaningful path starts at library_name
    bam_filename = bam_path[bam_path.find(library_name):]
    bai_filename = bai_path[bai_path.find(library_name):]

    # Prepend sample id to filenames
    bam_filename = os.path.join(sample.sample_id, bam_filename)
    bai_filename = os.path.join(sample.sample_id, bai_filename)

    bam_file, created = tantalus.models.FileResource.objects.get_or_create(
        size=os.path.getsize(bam_path),
        created=pd.Timestamp(time.ctime(os.path.getmtime(bam_path)), tz='Canada/Pacific'),
        file_type=tantalus.models.FileResource.BAM,
        read_end=None,
        compression=tantalus.models.FileResource.UNCOMPRESSED,
        filename=bam_filename,
    )
    if created:
        bam_file.save()

    bam_instance, created = tantalus.models.FileInstance.objects.get_or_create(
        storage=storage,
        file_resource=bam_file,
        filename_override=bam_filename_override,
    )
    if created:
        bam_instance.save()
        new_file_instances.append(bam_instance)

    if os.path.exists(bai_path):
        bai_file, created = tantalus.models.FileResource.objects.get_or_create(
            size=os.path.getsize(bai_path),
            created=pd.Timestamp(time.ctime(os.path.getmtime(bai_path)), tz='Canada/Pacific'),
            file_type=tantalus.models.FileResource.BAM,
            read_end=None,
            compression=tantalus.models.FileResource.UNCOMPRESSED,
            filename=bai_filename,
        )
        if created:
            bai_file.save()

        bai_instance, created = tantalus.models.FileInstance.objects.get_or_create(
            storage=storage,
            file_resource=bai_file,
            filename_override=bai_filename_override,
        )
        if created:
            bai_instance.save()
            new_file_instances.append(bai_instance)

    else:
        bai_file = None
        bai_instance = None

    bam_dataset, created = tantalus.models.BamFile.objects.get_or_create(
        bam_file=bam_file,
        bam_index_file=bai_file,
    )
    if created:
        bam_dataset.save()

    reference_genomes = set()
    aligners = set()

    for lane_info in lane_infos:
        lane, created = tantalus.models.SequenceLane.objects.get_or_create(
            flowcell_id=lane_info['flowcell_code'],
            lane_number=lane_info['lane_number'],
            sequencing_centre=tantalus.models.SequenceLane.GSC,
            sequencing_instrument=lane_info['sequencing_instrument'],
            read_type=lane_info['read_type'],
        )
        if created:
            lane.save()

        read_group, created = tantalus.models.ReadGroup.objects.get_or_create(
            sample=sample,
            dna_library=library,
            index_sequence=lane_info['adapter_index_sequence'],
            sequence_lane=lane,
            sequencing_library_id=library.library_id,
        )
        if created:
            read_group.save()

        bam_dataset.read_groups.add(read_group)

        reference_genomes.add(lane_info['reference_genome'])
        aligners.add(lane_info['aligner'])

    if len(reference_genomes) > 1:
        bam_dataset.reference_genome = tantalus.models.BamFile.UNUSABLE
    elif len(reference_genomes) == 1:
        bam_dataset.reference_genome = list(reference_genomes)[0]
        bam_dataset.aligner = ', '.join(aligners)

    bam_dataset.save()

    return new_file_instances


def query_gsc_wgs_bams(query_info):
    gsc_api = GSCAPI()

    for library_id in query_info.library_ids:
        query_gsc_library(gsc_api, library_id)


def query_gsc_library(gsc_api, library_name):
    storage = tantalus.models.ServerStorage.objects.get(name='gsc')

    # ASSUMPTION: GSC stored files are pathed from root
    assert storage.storage_directory == '/'

    # Keep track of file instances for md5 check
    new_file_instances = []

    with django.db.transaction.atomic():
        library_infos = gsc_api.query('library?name={}'.format(library_name))

        for library_info in library_infos:
            protocol_info = gsc_api.query('protocol/{}'.format(library_info['protocol_id']))

            if library_info['protocol_id'] not in wgs_protocol_ids:
                print 'warning, protocol {}:{} not supported'.format(library_info['protocol_id'], protocol_info['extended_name'])
                continue

            sample_id = library_info['external_identifier']

            sample, created = tantalus.models.Sample.objects.get_or_create(
                sample_id=sample_id,
            )
            if created:
                sample.save()

            library_name = library_info['name']

            library, created = tantalus.models.DNALibrary.objects.get_or_create(
                library_id=library_name,
                library_type=tantalus.models.DNALibrary.WGS,
                index_format=tantalus.models.DNALibrary.NO_INDEXING,
            )
            if created:
                library.save()

            merge_infos = gsc_api.query('merge?library={}'.format(library_name))

            # Keep track of lanes that are in merged BAMs so that we
            # can exclude them from the lane specific BAMs we add to
            # the database
            merged_lanes = set()

            for merge_info in merge_infos:
                data_path = merge_info['data_path']
                num_lanes = len(merge_info['merge_xrefs'])
                lane_pluralize = ('', 's')[num_lanes > 1]

                if data_path is None:
                    raise Exception('no data path for merge info {}'.format(merge_info['id']))

                bam_path = bam_path_template.format(
                    data_path=data_path,
                    library_name=library_name,
                    num_lanes=num_lanes,
                    lane_pluralize=lane_pluralize)

                if not os.path.exists(bam_path):
                    raise Exception('missing merged bam file {}'.format(bam_path))

                lane_infos = []

                for merge_xref in merge_info['merge_xrefs']:
                    libcore_id = merge_xref['object_id']

                    libcore = gsc_api.query('aligned_libcore/{}/info'.format(libcore_id))
                    flowcell_id = libcore['libcore']['run']['flowcell_id']
                    lane_number = libcore['libcore']['run']['lane_number']
                    sequencing_instrument = get_sequencing_instrument(libcore['libcore']['run']['machine'])
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

                new_file_instances += add_gsc_wgs_bam_dataset(bam_path, storage, sample, library, lane_infos)

            libcores = gsc_api.query('aligned_libcore/info?library={}'.format(library_name))

            for libcore in libcores:
                flowcell_id = libcore['libcore']['run']['flowcell_id']
                lane_number = libcore['libcore']['run']['lane_number']
                sequencing_instrument = get_sequencing_instrument(libcore['libcore']['run']['machine'])
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

                bam_path = lane_bam_path_template.format(
                    data_path=data_path,
                    flowcell_code=flowcell_code,
                    lane_number=lane_number,
                    adapter_index_sequence=adapter_index_sequence)

                if not os.path.exists(bam_path):
                    raise Exception('missing lane bam file {}'.format(bam_path))

                lane_infos = [dict(
                    flowcell_code=flowcell_code,
                    lane_number=lane_number,
                    adapter_index_sequence=adapter_index_sequence,
                    sequencing_instrument=sequencing_instrument,
                    read_type=solexa_run_type_map[solexa_run_type],
                    reference_genome=reference_genome,
                    aligner=aligner,
                )]

                new_file_instances += add_gsc_wgs_bam_dataset(bam_path, storage, sample, library, lane_infos)

        django.db.transaction.on_commit(lambda: tantalus.utils.start_md5_checks(new_file_instances))


def reverse_complement(sequence):
    return str(sequence[::-1]).translate(string.maketrans('ACTGactg','TGACtgac'))


def decode_raw_index_sequence(raw_index_sequence, instrument, rev_comp_override):
    i7 = raw_index_sequence.split("-")[0]
    i5 = raw_index_sequence.split("-")[1]

    if rev_comp_override is not None:
        if rev_comp_override == 'i7,i5':
            pass
        elif 'i7,rev(i5)':
            i5 = reverse_complement(i5)
        elif 'rev(i7),i5':
            i7 = reverse_complement(i7)
        elif 'rev(i7),rev(i5)':
            i7 = reverse_complement(i7)
            i5 = reverse_complement(i5)
        else:
            raise Exception('unknown override {}'.format(rev_comp_override))

        return i7 + '-' + i5

    if instrument == 'HiSeqX':
        i7 = reverse_complement(i7)
        i5 = reverse_complement(i5)
    elif instrument == 'HiSeq2500':
        i7 = reverse_complement(i7)
    elif instrument == 'NextSeq550':
        i7 = reverse_complement(i7)
        i5 = reverse_complement(i5)
    else:
        raise Exception('unsupported sequencing instrument {}'.format(instrument))

    return i7 + '-' + i5


def query_colossus_dlp_cell_info(library_id):

    sublibraries = get_colossus_sublibraries_from_library_id(library_id)

    cell_samples = {}
    for sublib in sublibraries:
        index_sequence = sublib['primer_i7'] + '-' + sublib['primer_i5']
        cell_samples[index_sequence] = sublib['sample_id']['sample_id']

    return cell_samples


def query_colossus_dlp_rev_comp_override(library_id):
    library_info = query_libraries_by_library_id(library_id)

    rev_comp_override = {}
    for sequencing in library_info['dlpsequencing_set']:
        for lane in sequencing['dlplane_set']:
            rev_comp_override[lane['flow_cell_id']] = sequencing['dlpsequencingdetail']['rev_comp_override']

    return rev_comp_override


# Mapping from filename pattern to read end, pass/fail
filename_pattern_map = {
    '_1.fastq.gz': (1, True),
    '_1_*.concat_chastity_passed.fastq.gz': (1, True),
    '_1_chastity_passed.fastq.gz': (1, True),
    '_1_chastity_failed.fastq.gz': (1, False),
    '_2.fastq.gz': (2, True),
    '_2_*.concat_chastity_passed.fastq.gz': (2, True),
    '_2_chastity_passed.fastq.gz': (2, True),
    '_2_chastity_failed.fastq.gz': (2, False),
}


def query_gsc_dlp_paired_fastqs(query_info):
    dlp_library_id = query_info.dlp_library_id
    gsc_library_id = query_info.gsc_library_id
    storage = tantalus.models.ServerStorage.objects.get(name='gsc')

    cell_samples = query_colossus_dlp_cell_info(dlp_library_id)
    rev_comp_overrides = query_colossus_dlp_rev_comp_override(dlp_library_id)

    # ASSUMPTION: GSC stored files are pathed from root
    assert storage.storage_directory == '/'

    gsc_api = GSCAPI()

    # Keep track of file instances for md5 check
    new_file_instances = []

    with django.db.transaction.atomic():
        fastq_infos = gsc_api.query('fastq?parent_library={}'.format(gsc_library_id))

        paired_fastq_infos = collections.defaultdict(dict)

        for fastq_info in fastq_infos:
            if fastq_info['status'] != 'production':
                continue

            fastq_path = fastq_info['data_path']
            flowcell_code = fastq_info['libcore']['run']['flowcell']['lims_flowcell_code']
            lane_number = fastq_info['libcore']['run']['lane_number']
            sequencing_instrument = get_sequencing_instrument(fastq_info['libcore']['run']['machine'])
            solexa_run_type = fastq_info['libcore']['run']['solexarun_type']

            primer_id = fastq_info['libcore']['primer_id']
            primer_info = gsc_api.query('primer/{}'.format(primer_id))
            raw_index_sequence = primer_info['adapter_index_sequence']

            flowcell_lane = flowcell_code
            if lane_number is not None:
                flowcell_lane = flowcell_lane + '_' + str(lane_number)

            rev_comp_override = rev_comp_overrides.get(flowcell_lane)

            index_sequence = decode_raw_index_sequence(raw_index_sequence, sequencing_instrument, rev_comp_override)

            filename_pattern = fastq_info['file_type']['filename_pattern']
            read_end, passed = filename_pattern_map.get(filename_pattern, (None, None))

            if read_end is None:
                raise Exception('Unrecognized file type: {}'.format(filename_pattern))

            if not passed:
                continue

            # ASSUMPTION: GSC stored files are pathed from root 
            fastq_filename_override = fastq_path

            # ASSUMPTION: meaningful path starts at library_name
            fastq_filename = fastq_path[fastq_path.find(gsc_library_id):]
            # Prepend single_cell_indexing/<gsc_lib_id>/ so it follows our file structure
            fastq_filename = 'single_cell_indexing/HiSeq/' + fastq_filename

            try:
                cell_sample_id = cell_samples[index_sequence]
            except KeyError:
                raise Exception('unable to find index {} for flowcell lane {} for library {}'.format(
                    index_sequence, flowcell_lane, dlp_library_id))

            sample, created = tantalus.models.Sample.objects.get_or_create(
                sample_id=cell_sample_id,
            )
            if created:
                sample.save()

            library, created = tantalus.models.DNALibrary.objects.get_or_create(
                library_id=dlp_library_id,
                library_type=tantalus.models.DNALibrary.SINGLE_CELL_WGS,
                index_format=tantalus.models.DNALibrary.DUAL_INDEX,
            )
            if created:
                library.save()

            lane, created = tantalus.models.SequenceLane.objects.get_or_create(
                flowcell_id=flowcell_code,
                lane_number=lane_number,
                sequencing_centre=tantalus.models.SequenceLane.GSC,
                sequencing_instrument=sequencing_instrument,
                read_type=solexa_run_type_map[solexa_run_type],
            )
            if created:
                lane.save()

            read_group, created = tantalus.models.ReadGroup.objects.get_or_create(
                sample=sample,
                dna_library=library,
                index_sequence=index_sequence,
                sequence_lane=lane,
                sequencing_library_id=gsc_library_id,
            )
            if created:
                read_group.save()

            fastq_file, created = tantalus.models.FileResource.objects.get_or_create(
                size=os.path.getsize(fastq_path),
                created=pd.Timestamp(time.ctime(os.path.getmtime(fastq_path)), tz='Canada/Pacific'),
                file_type=tantalus.models.FileResource.FQ,
                read_end=read_end,
                compression=tantalus.models.FileResource.GZIP,
                filename=fastq_filename,
            )
            if created:
                fastq_file.save()

            fastq_instance, created = tantalus.models.FileInstance.objects.get_or_create(
                storage=storage,
                file_resource=fastq_file,
                filename_override=fastq_filename_override,
            )
            if created:
                fastq_instance.save()
                new_file_instances.append(fastq_instance)

            fastq_id = (index_sequence, flowcell_code, lane_number)

            if read_end in paired_fastq_infos[fastq_id]:
                raise Exception('duplicate fastq end {} for {}'.format(read_end, fastq_id))

            paired_fastq_infos[fastq_id][read_end] = {
                'fastq_file':fastq_file,
                'read_group':read_group,
            }

        for fastq_id, paired_fastq_info in paired_fastq_infos.iteritems():
            if set(paired_fastq_info.keys()) != set([1, 2]):
                raise Exception('expected read end 1, 2 for {}, got {}'.format(fastq_id, paired_fastq_info.keys()))

            if paired_fastq_info[1]['read_group'].id != paired_fastq_info[2]['read_group'].id:
                raise Exception('expected same lane for {}'.format(fastq_id))

            fastq_dataset, created = tantalus.models.PairedEndFastqFiles.objects.get_or_create(
                reads_1_file=paired_fastq_info[1]['fastq_file'],
                reads_2_file=paired_fastq_info[2]['fastq_file'],
            )
            if created:
                fastq_dataset.save()

            fastq_dataset.read_groups.add(paired_fastq_info[1]['read_group'])
            fastq_dataset.save()

        django.db.transaction.on_commit(lambda: tantalus.utils.start_md5_checks(new_file_instances))


if __name__ == '__main__':
    query_gsc_dlp_paired_fastqs('A90696ABC')


