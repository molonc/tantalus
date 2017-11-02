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


wgs_protocol_ids = (
    12,
    136,
    140,
    123,
)


solexa_run_type_map = {
    'Paired': tantalus.models.SequenceLane.PAIRED}


raw_instrument_map = {
    'HiSeq': 'HiSeq2500',
    'HiSeqX': 'HiSeqX',
}


def get_sequencing_instrument(machine):
    """ Sequencing instrument decode.

    Example machines are HiSeq-27 or HiSeqX-2.
    """
    raw_instrument = machine.split('-')[0]
    return raw_instrument_map[raw_instrument]


class MissingFileError(Exception):
    pass


def query_gsc_wgs_bams(query_info):
    sample = query_info.sample
    storage = tantalus.models.ServerStorage.objects.get(name='gsc')

    # ASSUMPTION: GSC stored files are pathed from root
    assert storage.storage_directory == '/'

    gsc_api = GSCAPI()

    library_infos = gsc_api.query('library?external_identifier={}'.format(sample_id))

    # Keep track of file instances for
    new_file_instances = []

    with django.db.transaction.atomic():
        for library_info in library_infos:
            protocol_info = gsc_api.query('protocol/{}'.format(library_info['protocol_id']))

            if library_info['protocol_id'] not in wgs_protocol_ids:
                print 'warning, protocol {}:{} not supported'.format(library_info['protocol_id'], protocol_info['extended_name'])
                continue

            library_name = library_info['name']

            library, created = tantalus.models.DNALibrary.objects.get_or_create(
                library_id=library_name,
                library_type=tantalus.models.DNALibrary.WGS,
                index_format=tantalus.models.DNALibrary.NO_INDEXING,
            )
            if created:
                library.save()

            dna_sequences, created = tantalus.models.DNASequences.objects.get_or_create(
                dna_library=library,
                sample=sample,
                index_sequence=None,
            )
            if created:
                dna_sequences.save()

            merge_infos = gsc_api.query('merge?library={}'.format(library_name))

            for merge_info in merge_infos:
                data_path = merge_info['data_path']
                num_lanes = len(merge_info['merge_xrefs'])
                lane_pluralize = ('', 's')[num_lanes > 1]

                if data_path is None:
                    print 'warning: no data path for merge info {}'.format(merge_info['id'])
                    continue

                bam_path = bam_path_template.format(
                    data_path=data_path,
                    library_name=library_name,
                    num_lanes=num_lanes,
                    lane_pluralize=lane_pluralize)
                bai_path = bam_path + '.bai'

                if not os.path.exists(bam_path):
                    print 'warning: missing file {}'.format(bam_path)
                    continue

                if not os.path.exists(bai_path):
                    print 'warning: missing file {}'.format(bai_path)
                    continue

                # ASSUMPTION: GSC stored files are pathed from root 
                bam_filename_override = bam_path
                bai_filename_override = bai_path

                # ASSUMPTION: meaningful path starts at library_name
                bam_filename = bam_path[bam_path.find(library_name):]
                bai_filename = bai_path[bai_path.find(library_name):]

                # Prepend sample id to filenames
                bam_filename = os.path.join(sample_id, bam_filename)
                bai_filename = os.path.join(sample_id, bai_filename)

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

                bam_instance, created = tantalus.models.FileInstance.objects.get_or_create(
                    storage=storage,
                    file_resource=bam_file,
                    filename_override=bam_filename_override,
                )
                if created:
                    bam_instance.save()
                    new_file_instances.append(bam_instance)

                bai_instance, created = tantalus.models.FileInstance.objects.get_or_create(
                    storage=storage,
                    file_resource=bai_file,
                    filename_override=bai_filename_override,
                )
                if created:
                    bai_instance.save()
                    new_file_instances.append(bai_instance)

                bam_dataset, created = tantalus.models.BamFile.objects.get_or_create(
                    bam_file=bam_file,
                    bam_index_file=bai_file,
                    dna_sequences=dna_sequences,
                )
                if created:
                    bam_dataset.save()

                reference_genomes = set()
                aligners = set()

                for merge_xref in merge_info['merge_xrefs']:
                    libcore_id = merge_xref['object_id']

                    libcore = gsc_api.query('aligned_libcore/{}/info'.format(libcore_id))
                    flowcell_id = libcore['libcore']['run']['flowcell_id']
                    lane_number = libcore['libcore']['run']['lane_number']
                    sequencing_instrument = get_sequencing_instrument(libcore['libcore']['run']['machine'])
                    solexa_run_type = libcore['libcore']['run']['solexarun_type']
                    reference_genome = libcore['lims_genome_reference']['path']
                    aligner = libcore['analysis_software']['name']

                    reference_genomes.add(reference_genome)
                    aligners.add(aligner)

                    flowcell_info = gsc_api.query('flowcell/{}'.format(flowcell_id))
                    flowcell_code = flowcell_info['lims_flowcell_code']

                    lane, created = tantalus.models.SequenceLane.objects.get_or_create(
                        flowcell_id=flowcell_code,
                        lane_number=lane_number,
                        sequencing_centre=tantalus.models.SequenceLane.GSC,
                        sequencing_library_id=library_name,
                        sequencing_instrument=sequencing_instrument,
                        read_type=solexa_run_type_map[solexa_run_type],
                        dna_library=library,
                    )
                    if created:
                        lane.save()

                    bam_dataset.lanes.add(lane)

                if len(reference_genomes) > 1:
                    bam_dataset.reference_genome = tantalus.models.BamFile.UNUSABLE
                elif len(reference_genomes) == 1:
                    bam_dataset.reference_genome = list(reference_genomes)[0]
                    bam_dataset.aligner = ', '.join(aligners)

                bam_dataset.save()

        django.db.transaction.on_commit(lambda: tantalus.utils.start_md5_checks(new_file_instances))


def reverse_complement(sequence):
    return str(sequence[::-1]).translate(string.maketrans('ACTGactg','TGACtgac'))


def decode_raw_index_sequence(raw_index_sequence, instrument):
    i7 = raw_index_sequence.split("-")[0]
    i5 = raw_index_sequence.split("-")[1]

    if instrument == 'HiSeqX':
        i7 = reverse_complement(i7)
        i5 = reverse_complement(i5)
    elif instrument == 'HiSeq2500':
        i7 = reverse_complement(i7)
    else:
        raise Exception('unsupported sequencing instrument {}'.format(instrument))

    return i7 + '-' + i5


LIMS_API = "http://10.9.215.82:7000/apps/api/"


def query_colossus_dlp_cell_info(library_id):
    # library_id = 'A90696ABC'
    library_url = 'http://10.9.215.82:7000/apps/api/library/?pool_id={}'.format(library_id)

    r = requests.get(library_url)

    if r.status_code != 200:
        raise Exception('Returned {}: {}'.format(r.status_code, r.reason))

    if len(r.json()) == 0:
        raise Exception('No entries for library {}'.format(library_id))

    if len(r.json()) > 1:
        raise Exception('Multiple entries for library {}'.format(library_id))

    data = r.json()[0]

    primary_sample_id = data['sample']['sample_id']

    cell_samples = {}
    for sublib in data['sublibraryinformation_set']:
        index_sequence = sublib['primer_i7'] + '-' + sublib['primer_i5']
        cell_samples[index_sequence] = sublib['sample_id']['sample_id']

    return primary_sample_id, cell_samples


def query_gsc_dlp_paired_fastqs(query_info):
    dlp_library_id = query_info.dlp_library_id
    storage = tantalus.models.ServerStorage.objects.get(name='gsc')

    primary_sample_id, cell_samples = query_colossus_dlp_cell_info(dlp_library_id)
    gsc_external_id = primary_sample_id + '_' + dlp_library_id

    # ASSUMPTION: GSC stored files are pathed from root
    assert storage.storage_directory == '/'

    gsc_api = GSCAPI()

    library_infos = gsc_api.query('library?external_identifier={}'.format(gsc_external_id))
    if len(library_infos) > 1:
        raise Exception('multiple gsc libraries for {}'.format(gsc_external_id))
    elif len(library_infos) == 0:
        raise Exception('no gsc libraries for {}'.format(gsc_external_id))

    gsc_library_id = library_infos[0]['name']

    # Keep track of file instances for
    new_file_instances = []

    with django.db.transaction.atomic():
        fastq_infos = gsc_api.query('fastq?parent_library={}'.format(gsc_library_id))

        paired_fastq_infos = collections.defaultdict(dict)

        for fastq_info in fastq_infos:
            name = fastq_info['libcore']['library']['name']
            fastq_path = fastq_info['data_path']
            flowcell_code = fastq_info['libcore']['run']['flowcell']['lims_flowcell_code']
            lane_number = fastq_info['libcore']['run']['lane_number']
            sequencing_instrument = get_sequencing_instrument(fastq_info['libcore']['run']['machine'])
            solexa_run_type = fastq_info['libcore']['run']['solexarun_type']

            raw_index_sequence = name.split('_')[1]
            index_sequence = decode_raw_index_sequence(raw_index_sequence, sequencing_instrument)

            file_type = fastq_info['file_type']['filename_pattern']
            if file_type == '_1.fastq.gz':
                read_end = 1
            elif file_type == '_2.fastq.gz':
                read_end = 2
            else:
                raise Exception('Unrecognized file type: {}'.format(file_type))

            # ASSUMPTION: GSC stored files are pathed from root 
            fastq_filename_override = fastq_path

            # ASSUMPTION: meaningful path starts at library_name
            fastq_filename = fastq_path[fastq_path.find(gsc_library_id):]

            cell_sample_id = cell_samples[index_sequence]

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

            dna_sequences, created = tantalus.models.DNASequences.objects.get_or_create(
                dna_library=library,
                sample=sample,
                index_sequence=index_sequence,
            )
            if created:
                dna_sequences.save()

            lane, created = tantalus.models.SequenceLane.objects.get_or_create(
                flowcell_id=flowcell_code,
                lane_number=lane_number,
                sequencing_centre=tantalus.models.SequenceLane.GSC,
                sequencing_library_id=gsc_library_id,
                sequencing_instrument=sequencing_instrument,
                read_type=solexa_run_type_map[solexa_run_type],
                dna_library=library,
            )
            if created:
                lane.save()

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

            fastq_id = (name, flowcell_code, lane_number)

            if read_end in paired_fastq_infos[fastq_id]:
                raise Exception('duplicate fastq end {} for {}'.format(read_end, fastq_id))

            paired_fastq_infos[fastq_id][read_end] = {
                'fastq_file':fastq_file,
                'dna_sequences':dna_sequences,
                'lane':lane,
            }

        for fastq_id, paired_fastq_info in paired_fastq_infos.iteritems():
            if set(paired_fastq_info.keys()) != set([1, 2]):
                raise Exception('expected read end 1, 2 for {}, got {}'.format(fastq_id, paired_fastq_info.keys()))

            if paired_fastq_info[1]['dna_sequences'].id != paired_fastq_info[2]['dna_sequences'].id:
                raise Exception('expected same dna sequences for {}'.format(fastq_id))

            if paired_fastq_info[1]['lane'].id != paired_fastq_info[2]['lane'].id:
                raise Exception('expected same lane for {}'.format(fastq_id))

            fastq_dataset, created = tantalus.models.PairedEndFastqFiles.objects.get_or_create(
                reads_1_file=paired_fastq_info[1]['fastq_file'],
                reads_2_file=paired_fastq_info[2]['fastq_file'],
                dna_sequences=paired_fastq_info[1]['dna_sequences'],
            )
            if created:
                fastq_dataset.save()

            fastq_dataset.lanes.add(paired_fastq_info[1]['lane'])
            fastq_dataset.save()

        django.db.transaction.on_commit(lambda: tantalus.utils.start_md5_checks(new_file_instances))


if __name__ == '__main__':
    query_gsc_dlp_paired_fastqs('A90696ABC')


