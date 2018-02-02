from collections import Counter
from datetime import datetime
import os
import sys
import string
import pandas as pd
import django
import re
import ast
import requests
import pytz

sys.path.append('./')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tantalus.settings')
django.setup()
DIRECTORY_TO_STRIP = "/share/lustre/archive/single_cell_indexing/HiSeq/"

from tantalus.models import *
from tantalus.gsc_queries import add_gsc_wgs_bam_dataset
from tantalus.utils import start_md5_checks

def get_genome_version(genome):
    if '/' in genome:
        return genome.split('/')[0]


library = {'illumina_wgss': 'WGS', 'illumina_wtss': 'RNASEQ', 'illumina_exoncapture': 'EXOME', 'exon_capture': 'EXOME',
           'illumina_amplicon': "AMPLICON", 'illumina_chip': 'CHIP', 'illumina_bisulfite': 'BISULFITE'}


def translate_library_type(type):
    return library[type]


def create_bam_file(lanes, sequences, reference_genome, aligner, ):
    BamFile.objects.create(
        lanes=lanes,
        sequences=sequences,
        reference_genome=reference_genome,
        aligner=aligner
    )

wgs_protocol_ids = (
   12,
   73,
   76,
   112,
   123,
   136,
   140,
)

bam_path_template = '{data_path}/{library_name}_{num_lanes}_lane{lane_pluralize}_dupsFlagged.bam'
lane_bam_path_template = '{data_path}/{flowcell_code}_{lane_number}_{adapter_index_sequence}.bam'
GSC_API_URL = "http://sbs:8100/"

solexa_run_type_map = {
    'Paired': SequenceLane.PAIRED}

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

def query_gsc_wgs_bam_library(library_name, sample_id):
    request_handle = requests.Session()
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    response = request_handle.post("http://sbs:8100/session",
                                   json={'username': django.conf.settings.GSC_API_USERNAME,
                                         'password': django.conf.settings.GSC_API_PASSWORD}, headers=headers).json()
    token = response.get('token')
    headers.update({'X-Token': token})

    storage = ServerStorage.objects.get(name='gsc')

    new_file_instances=[]

    with django.db.transaction.atomic():
        library, created = DNALibrary.objects.get_or_create(
            library_id=library_name,
            library_type=DNALibrary.WGS,
            index_format=DNALibrary.NO_INDEXING,
        )
        if created:
            library.save()

        sample, created = Sample.objects.get_or_create(
            sample_id = sample_id
        )

        dna_sequences, created = DNASequences.objects.get_or_create(
            dna_library=library,
            sample=sample,
            index_sequence=None,
        )
        if created:
            dna_sequences.save()

        merge_infos = request_handle.get(GSC_API_URL + 'merge?library={}'.format(library_name), headers=headers).json()

        # Keep track of lanes that are in merged BAMs so that we
        # can exclude them from the lane specific BAMs we add to
        # the database
        merged_lanes = set()

        for merge_info in merge_infos:
            print(merge_info)
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
                print(sample_id)
                print ('missing merged bam file {}'.format(bam_path))
                continue

            lane_infos = []

            for merge_xref in merge_info['merge_xrefs']:
                libcore_id = merge_xref['object_id']

                libcore = request_handle.get((GSC_API_URL + 'aligned_libcore/{}/info'.format(libcore_id)), headers=headers).json()
                flowcell_id = libcore['libcore']['run']['flowcell_id']
                lane_number = libcore['libcore']['run']['lane_number']
                sequencing_instrument = get_sequencing_instrument(libcore['libcore']['run']['machine'])
                solexa_run_type = libcore['libcore']['run']['solexarun_type']
                reference_genome = libcore['lims_genome_reference']['path']
                aligner = libcore['analysis_software']['name']
                flowcell_info = request_handle.get(GSC_API_URL + 'flowcell/{}'.format(flowcell_id), headers=headers).json()
                # flowcell_info = gsc_api.query('flowcell/{}'.format(flowcell_id))
                flowcell_code = flowcell_info['lims_flowcell_code']

                merged_lanes.add((flowcell_code, lane_number))

                lane_info = dict(
                    flowcell_code=flowcell_code,
                    lane_number=lane_number,
                    sequencing_instrument=sequencing_instrument,
                    read_type=solexa_run_type_map[solexa_run_type],
                    reference_genome=reference_genome,
                    aligner=aligner,
                )

                lane_infos.append(lane_info)

                try:
                    new_file_instances += add_gsc_wgs_bam_dataset(bam_path, storage, sample_id, library, dna_sequences, lane_infos)
                except:
                    print(lane_info)
                    raise

        print(merged_lanes)

        libcores = request_handle.get(GSC_API_URL + 'aligned_libcore/info?library={}'.format(library_name), headers=headers).json()

        for libcore in libcores:
            flowcell_id = libcore['libcore']['run']['flowcell_id']
            lane_number = libcore['libcore']['run']['lane_number']
            sequencing_instrument = get_sequencing_instrument(libcore['libcore']['run']['machine'])
            solexa_run_type = libcore['libcore']['run']['solexarun_type']
            reference_genome = libcore['lims_genome_reference']['path']
            aligner = libcore['analysis_software']['name']
            adapter_index_sequence = libcore['libcore']['primer']['adapter_index_sequence']
            data_path = libcore['data_path']

            flowcell_info = request_handle.get(GSC_API_URL + 'flowcell/{}'.format(flowcell_id), headers=headers).json()
            flowcell_code = flowcell_info['lims_flowcell_code']

            # Skip lanes that are part of merged BAMs
            if (flowcell_code, lane_number) in merged_lanes:
                continue

            bam_path = lane_bam_path_template.format(
                data_path=data_path,
                flowcell_code=flowcell_code,
                lane_number=lane_number,
                adapter_index_sequence=adapter_index_sequence)

            if not os.path.exists(bam_path):
                print('missing lane bam file {}'.format(bam_path))
                continue
                # raise Exception('missing lane bam file {}'.format(bam_path))

            lane_infos = [dict(
                flowcell_code=flowcell_code,
                lane_number=lane_number,
                sequencing_instrument=sequencing_instrument,
                read_type=solexa_run_type_map[solexa_run_type],
                reference_genome=reference_genome,
                aligner=aligner,
            )]

            new_file_instances += add_gsc_wgs_bam_dataset(bam_path, storage, sample_id, library, dna_sequences, lane_infos)

        django.db.transaction.on_commit(lambda: start_md5_checks(new_file_instances))


rocks = Storage.objects.get(name="rocks")

def create_new_bamfile(line, sequence_lanes, dna_sequence, added_to_tantalus, new_file_instances):
    assert '/share/lustre/archive/' in line.path

    tz = pytz.timezone('Canada/Pacific')
    bam_file_resource = FileResource(
        size=line.bytes,
        created=tz.localize(datetime.strptime(line.created, 'Modify: %Y-%m-%d %H:%M:%S.00000000')),
        file_type=FileResource.BAM,
        compression=FileResource.UNCOMPRESSED,
        filename=line.path[len('/share/lustre/archive/'):]
    )
    try:
        bam_file_resource.save()
    except django.db.utils.IntegrityError:
        print 'failed for ', line.path

    bam_file_instance = FileInstance(
        storage=rocks,
        file_resource=bam_file_resource,
        filename_override=''
    )

    bam_file_instance.save()
    new_file_instances.append(bam_file_instance)

    if not pd.isnull(line['index_file']):
        assert '/share/lustre/archive/' in line.index_file

        bai_file_resource = FileResource(
            size=line.bytes,
            created=tz.localize(datetime.strptime(line['bai-created'], 'Modify: %Y-%m-%d %H:%M:%S.00000000')),
            file_type=FileResource.BAI,
            compression=FileResource.UNCOMPRESSED,
            filename=line.index_file[len('/share/lustre/archive/'):]
        )
        bai_file_resource.save()

        bai_file_instance = FileInstance(
            storage=rocks,
            file_resource=bai_file_resource,
            filename_override=''
        )
        bai_file_instance.save()
        new_file_instances.append(bai_file_instance)

        bam = BamFile(
            dna_sequences=dna_sequence,
            aligner=line.aligner,
            bam_file=bam_file_resource,
            bam_index_file=bai_file_resource)
    else:
        bam = BamFile(
            dna_sequences=dna_sequence,
            aligner=line.aligner,
            bam_file=bam_file_resource)

    bam.save()
    bam.reference_genome = line.reference_genome
    bam.lanes = sequence_lanes
    bam.save()
    added_to_tantalus.append(line)


def load_into_tantalus():
    df = pd.DataFrame.from_csv("scrapers/bulk_bam_metadata.csv")

    query_failed = {}
    added_to_tantalus = []
    sample_id_mismatch = []
    no_lib = []
    no_seq = []
    no_bams_found = []
    different_size = []
    no_lanes = []
    multiple_bams_found = []
    new_file_instances = []

    for index, line in df.iterrows():
        print line

        # Uncomment this to get the gsc querying per line
        # try:
        #     query_gsc_wgs_bam_library(line.library_id, line.sample_id)
        # except Exception as e:
        #     print("Could not query GSC for Library {} and Sample {} for file {}".format(line.library_id, line.sample_id, line.path))
        #     print e.message
        #     query_failed[line.path] = e.message
        #     continue

        # These ones are skipped
        if line['library_type'] == "abi_solid" or line['library_type'] == 'illumina_mirna':
            continue

        # Uncomment this if you only want the files with lanes in them
        # if len(ast.literal_eval(line['lanes'])) == 0:
        #     no_lanes.append(line.path)
        #     print("No lanes fround for {}".format(line.path))
        #     continue

        if line.file == 'sorted.bam' or \
                'oldResults' in line.path or\
                line.path == '/share/lustre/archive/RG008N/illumina_wgss/A01458/bwa_aligned/RG008N_A01458_9_lanes_hg18_dupsFlagged.bam' or\
                line.path == '/share/lustre/archive/SA429/illumina_wgss/A11848_A21770/bwa_aligned/SA429_A11848_A21770_6_lanes_dupsFlagged_reheader.bam':
            continue
        if len(ast.literal_eval(line['lanes'])) != len(set(ast.literal_eval(line['lanes']))):
            continue

        with django.db.transaction.atomic():
            sample = line['sample_id']
            sample, created = Sample.objects.get_or_create(sample_id=sample)
            if created:
                sample.save()

            library_id = line['library_id']
            try:
                library = DNALibrary.objects.get(library_id=library_id)
            except:
                print("No DNALibrary for {}".format(library_id))
                no_lib.append(line['path'])
                continue

            dna_sequence, dna_sequence_created = DNASequences.objects.get_or_create(dna_library=library, sample=sample)
            if dna_sequence_created:
                dna_sequence.save()

            if dna_sequence.sample.sample_id != line['sample_id']:
                print("Different samples found ! Database: {} Scraped: {}. But continuing anyway".format(str(dna_sequence.sample.sample_id), line['sample_id']))
                sample_id_mismatch.append(line['path'])

            sequence_lanes = []
            # Get all the sequence lanes for the bamfile
            for lane in ast.literal_eval(line['lanes']):
                flowcell_id, lane_number = lane
                try:
                    sequence_lanes.append(SequenceLane.objects.get(flowcell_id=flowcell_id, lane_number=lane_number))
                except:
                    print("No sequence lanes found for flowcell {} and lane number {}".format(flowcell_id, lane_number))
                    print("SequenceLanes for Flowcell {}".format(SequenceLane.objects.filter(flowcell_id=flowcell_id)))
                    sl = SequenceLane(
                        lane_number=lane_number,
                        flowcell_id=flowcell_id,
                        sequencing_centre='GSC',
                        sequencing_library_id=library_id,
                        sequencing_instrument='unknown',
                        # Don't know if this is a good default.
                        read_type='P',
                        dna_library=library)
                    sl.save()
                    sequence_lanes.append(sl)

            # Filter BamFiles by DNA Sequence First
            dna_sequence_filtered_bams = BamFile.objects.filter(dna_sequences=dna_sequence)

            # If no BamFiles exist, create them
            if len(dna_sequence_filtered_bams) == 0:
                create_new_bamfile(line, sequence_lanes, dna_sequence, added_to_tantalus, new_file_instances)
                continue

            # Next filter against lanes and check sizes
            bam_file = []
            for bam in dna_sequence_filtered_bams:
                # Loop through each of the Sequence lanes and compare them against the lanes of the bamfile.
                # If all the lanes of the bamfile match, then add the bamfile
                add = True

                # Check to see there are the same amount of lanes from the database as the scraped bam file
                if len(bam.lanes.all()) != len(sequence_lanes):
                    # print("Different number of lanes.")
                    continue

                # Check that all the lanes from the database bam file are the same as the scraped bam file
                for lane in bam.lanes.all():
                    if lane not in sequence_lanes:
                        # print("Lane {} not in Sequence_lanes".format(vars(lane)))
                        add = False

                # Check the sizes
                if bam.bam_file.size != line.bytes:
                    different_size.append(line.path)
                    # print("Size is different. Database: {} Scraped: {}".format(bam.bam_file.size, line.bytes))
                    add = False

                if add:
                    bam_file.append(bam)
            # Check if the files is in there twice with different aligner TODO maybe?

            if len(bam_file) == 0:
                if len(dna_sequence_filtered_bams) > 0:
                    for bam in dna_sequence_filtered_bams:
                        print('lanes of bamfile: {}'.format(tuple(bam.lanes.all())))
                        print('lanes from metadata: {}'.format(sequence_lanes))
                        print('file: {}'.format(line['path']))
                        print(bam.bam_file)
                        print(bam.dna_sequences.sample)
                # no_bams_found.append(line['path'])
                # print ("No BamFiles found for Sequence: {} and Lanes {}.".format(dna_sequence, sequence_lanes))
                create_new_bamfile(line, sequence_lanes, dna_sequence, added_to_tantalus, new_file_instances)
                continue

            if len(bam_file) > 1:
                print(line['path'])
                print("More than 1 Bamfile for sequence {} and lanes {}".format(dna_sequence.sample.sample_id, sequence_lanes))
                multiple_bams_found.append(line['path'])
                continue

            bam_file_resource = FileResource.objects.get(id=bam_file[0].bam_file_id)

            # # Create the Bam instance
            # bam_file_instance, created=FileInstance.objects.get_or_create(
            #     storage=rocks,
            #     file_resource=bam_file_resource)
            #
            # bam_file_instance.filename_override = line['path']
            #
            # if created:
            #     bam_file_instance.save()
            #
            # # Create the Bam index Instance
            # if not pd.isnull(line['index_file']):
            #     bai_file_resource = FileResource.objects.get(id=bam_file[0].bam_index_file_id)
            #     bai_file_instance, created = FileInstance.objects.get_or_create(
            #         storage=rocks,
            #         file_resource=bai_file_resource)
            #     bai_file_instance.filename_override = line['index_file']
            #     if created:
            #         bai_file_instance.save()
            #
            # added_to_tantalus.append(line)
            django.db.transaction.on_commit(lambda: start_md5_checks(new_file_instances))


    print("# of files with a failed GSC Query: {}".format(len(query_failed)))
    print(query_failed)
    print("# of files with no lanes specified in them: {}".format(len(no_lanes)))
    print(no_lanes)
    print("# of sample id mismatch files: {}".format(len(sample_id_mismatch)))
    print(sample_id_mismatch)
    print('# of files with no DNALibrary: {}'.format(len(no_lib)))
    print(no_lib)
    print('# of files with no DNASequence: {}'.format(len(no_seq)))
    print(no_seq)
    print('# of no bam files found: {}'.format(len(no_bams_found)))
    print(no_bams_found)
    print('# of multiple bam files found: {}'.format(len(multiple_bams_found)))
    print(multiple_bams_found)
    print('# of bams with different size: {}'.format(len(different_size)))
    print(different_size)
    print('# actually added to tantalus: {}'.format(len(added_to_tantalus)))
    types = []
    for line in added_to_tantalus:
        types.append(line.library_type)
    print Counter(types)


if __name__ == '__main__':
    load_into_tantalus()
