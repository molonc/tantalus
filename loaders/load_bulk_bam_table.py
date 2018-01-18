from datetime import datetime
import os
import sys
import string
import pandas as pd
import django
import paramiko
import re
import ast
import itertools
import requests

sys.path.append('./')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tantalus.settings')
django.setup()
DIRECTORY_TO_STRIP = "/share/lustre/archive/single_cell_indexing/HiSeq/"

from tantalus.models import *
from tantalus.gsc_queries import add_gsc_wgs_bam_dataset
from tantalus.utils import start_md5_checks

# def _read_chrom_lengths(file, name, dict):
#     for line in file.readlines():
#         chr, len = line.strip().split('\t')
#         len = int(len)
#         if chr == 'chrM':
#             continue
#         if dict.has_key((chr, len)):
#             raise Exception("Chrom length not unique" + str((chr, len)))
#         dict[(chr, len)] = name
#
#
# def read_lengths():
#     lengths = {}
#     with open('scrapers/chromlengths_19.txt', 'r') as f:
#         _read_chrom_lengths(f, 'HG19', lengths)
#
#     with open('scrapers/chromlengths_18.txt', 'r') as f:
#         _read_chrom_lengths(f, 'HG18', lengths)
#
#     lengths[('chr1', 197195432)] = 'MM9'
#     lengths[('chr1', 195471971)] = 'MM10'
#
#     return lengths
#
#
# chrom_lengths = read_lengths()


# def reverse_complement(sequence):
#     return sequence[::-1].translate(string.maketrans('ACTGactg','TGACtgac'))


# def get_sam_header_information(file_to_bam):
#     #TODO: ask andrew for help
    # libraries = pd.HDFStore('loaders/single_cell_hiseq_fastq_metadata.h5', 'r')['/metadata']['id']
    # return libraries


# def get_or_create_scraped_samples(df):
#     # df = pd.DataFrame.from_csv('scrapers/bulk_bam.txt', sep='\t', index_col=None)
#     samples = set(df['sample_id'])
#     for s in samples:
#         tantalus.models.Sample.objects.get_or_create(
#             sample_id=s
#         )
#
#
# def get_or_create_scraped_dna_library(bulk_bam):
#     df = pd.DataFrame.from_csv('scrapers/bulk_bam.txt', sep='\t', index_col=None)
#     libs = set(df['library_id'])
#     for lib in libs:
#         tantalus.models.DNALibrary.objects.get_or_create(
#             library_id=lib,
#             #TODO: ask andrew what to fill in for the other fields of DNA Library..
#         )


def get_genome_version(genome):
    if '/' in genome:
        return genome.split('/')[0]


# def determine_genome_by_length(sequence_name, length):
#     try:
#         return chrom_lengths[(sequence_name, length)]
#     except KeyError:
#         raise Exception("Could not determine chromosome for length: " + sequence_name + ' ' + str(length))


# def standardize_names(name):
#     match = re.match('^[\dMXYT]+$', name)
#     if match:
#         return 'chr' + name
#     return name


# def get_reference_genome_for_line(line):
#     # Check if genome is specified
#     # name = re.match('^.*AS:([\w/]+)\t?.*$', line)
#     # if name:
#     #     genome = get_genome_version(name.group(1))
#     # If not, then determine it based on chromosone lengths
#     # else:
#     length = re.match('^.*LN:(\d+)\t?.*$', line)
#     if length:
#         sequence_name = standardize_names(re.match('^.*SN:([^\t.]*)\t.*', line).group(1))
#         # Ignore chromosome M
#         if sequence_name == 'chrM' or sequence_name == 'chrMT':
#             return 'M'
#         genome = determine_genome_by_length(sequence_name, int(length.group(1)))
#     return genome


# def find_lines(pattern, lines):
#     return list(filter(lambda x: x.startswith(pattern), lines.splitlines(False)))


# def get_reference_genome(out):
#     ReferenceSequences = find_lines('@SQ', out)
#     if len(ReferenceSequences) == 0:
#         return 'ignore'
#     chr1 = list(filter(lambda x: 'SN:1\t' in x or 'SN:chr1\t' in x, ReferenceSequences))[0]
#     return get_reference_genome_for_line(chr1)


# def get_aligner(out):
#     aligner_lines = find_lines('@PG', out)
#     # Check if program name exists
#     aligner = ""
#     version = ""
#
#     # Look for program name first
#     for line in aligner_lines:
#         match = re.match('.*(PN:)\t?.*$', line)
#         if match:
#             if 'bwa' in match.group(1):
#                 aligner = match.group(1)[3:]
#
#
#     # If it can't find program name then look for CL
#     if aligner == "":
#         for line in aligner_lines:
#             match = re.match('.*(CL:bwa.*)\t.*$', line)
#             if match:
#                 aligner = match.group(1)[3:]
#                 match = re.match('.*(VN:)\t.*', line)
#                 if match:
#                     version = match.group(1)[3:]
#     return aligner, version


# def get_lanes(out):
#     lanes = []
#     lane_lines = find_lines('@RG', out)
#     for line in lane_lines:
#         technology = re.match('.*PL:(\w+)\t?.*$', line)
#         if technology:
#             if technology.group(1) == "illumina":
#                 full_flowcell = re.match('.*PU:(\w+).(\d)', line)
#                 if full_flowcell is None:
#                     return "ignore"
#                 flowcell_id = full_flowcell.group(1)
#                 lane_number = full_flowcell.group(2)
#                 lanes.append((flowcell_id, lane_number))
#             else:
#                 return "ignore"
#     return lanes
#
#
# def get_center(out):
#     center_lines = find_lines('@RG', out)
#     sequencing_center = []
#     for line in center_lines:
#         center = re.match('.*CN:(\w+)\t?.*$', line)
#         if center:
#             sequencing_center.append(center.group(1))
#
#     return list(set(sequencing_center))
#
#
# def get_library_from_header(out):
#     library_lines = find_lines('@RG', out)
#     library = []
#     for line in library_lines:
#         lib = re.match('.*LB(\w+)\t?.*$', line)
#         if lib: library.append(lib.group(1))
#     return library


# def get_remote_metadata(bulk_bam):
#     client = paramiko.SSHClient()
#     client.load_system_host_keys()
#     client.connect(
#         'beast.cluster.bccrc.ca',
#         username='tchan'
#     )
#
#     df = pd.DataFrame(columns=['sample_id', 'library_type', 'library_id', 'file_type', 'file', 'bytes', 'path', 'index_file', 'bai_bytes', 'notes',
#     #                            'reference_genome', 'aligner', 'lanes'])
#     for idx, line in df.iterrows():
#         if 'TASK' in line.path:
#             continue
#         stdin, stdout, stderr = client.exec_command("samtools view -H {}".format(line.path))
#         if stderr.channel.recv_exit_status() != 0:
#             print stderr.read()
#             raise Exception("Non zero exit on line {}".format(line))
#
#         sam_header = stdout.read()
#
#         # Get Genome
#         reference_genome = get_reference_genome(sam_header)
#         if reference_genome == "ignore":
#             continue
#         if reference_genome == "None found" or reference_genome == "More than 1":
#             raise Exception(reference_genome)
#         #
#         # # Get Aligner
#         aligner, version = get_aligner(sam_header)
#         #
#         # # Get Lanes
#         lanes = get_lanes(sam_header)
#         if lanes == "ignore":
#             continue
#
#         # Get Sequencing Center
#         center = get_center(sam_header)
#
#         # See what the file says is it's libary
#         file_library = get_library_from_header(sam_header)
#
#         # Get creation time
#         # stdin, stdout, stderr = client.exec_command("stat {}".format(line.path))
#
#         Modify = stdout.readlines()[5][:-8]
#
#         line['created'] = Modify
#
#         # Check for bai file
#         stdin, stdout, stderr = client.exec_command("stat {}.bai".format(line.path))
#         if stderr.channel.recv_exit_status() != 0:
#             print stderr.read()
#             raise Exception("Non zero exit on line {}".format(line.path + '.bai'))
#
#         if len(stderr.read()) == 0:
#             line['index_file'] = line.path + '.bai'
#             # line['bai_bytes'] = int(full_ll.split('\t')[0])
#             out = stdout.readlines()[1]
#             line['bai_bytes'] = int(re.match('^.*Size: (\d+).*$', out).group(1))
#
#             stdin, stdout, stderr = client.exec_command("stat {}.bai".format(line.path))
#
#             Modify = stdout.readlines()[5][:-8]
#
#             line['bai-created'] = Modify
#         else:
#             line['index_file'] = "N/A"
#
#         line['reference_genome'] = reference_genome
#         line['aligner'] = aligner
#         line['aligner_version'] = version
#         line['lanes'] = lanes
#         line['center'] = center
#         line['file_libary'] = file_library
#
#         df = df.append(line)
#     df.to_csv('scrapers/bulk_bam_metadata.csv')


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

def load_into_tantalus():
    df = pd.DataFrame.from_csv("scrapers/bulk_bam_metadata.csv")

    storage = Storage.objects.get(name="rocks")

    query_failed = {}
    added_to_tantalus = []
    sample_id_mismatch = []
    no_lib = []
    no_seq = []
    no_bams_found = []
    different_size = []
    no_lanes = []
    multiple_bams_found = []

    for index, line in df.iterrows():
        # Uncomment this to get the gsc querying per line
        try:
            query_gsc_wgs_bam_library(line.library_id, line.sample_id)
        except Exception as e:
            print("Could not query GSC for Library {} and Sample {} for file {}".format(line.library_id, line.sample_id, line.path))
            print e.message
            query_failed[line.path] = e.message
            continue

        # These ones are skipped
        if line['library_type'] == "abi_solid" or line['library_type'] == 'illumina_mirna':
            continue

        if len(ast.literal_eval(line['lanes'])) == 0:
            no_lanes.append(line.path)
            print("No lanes fround for {}".format(line.path))
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

            try:
                dna_sequence = DNASequences.objects.get(dna_library=library)
            except:
                print("No DNASequence for {}".format(library_id))
                no_seq.append(line['path'])
                continue

            if dna_sequence.sample.sample_id != line['sample_id']:
                print("Different samples found ! Database: {} Scraped: {}".format(str(dna_sequence.sample.sample_id), line['sample_id']))
                sample_id_mismatch.append(line['path'])
                continue

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

            # Next filter against lanes and check sizes
            bam_file = []
            for bam in dna_sequence_filtered_bams:
                print(vars(bam))
                # Loop through each of the Sequence lanes and compare them against the lanes of the bamfile.
                # If all the lanes of the bamfile match, then add the bamfile
                add = True

                # Check to see there are the same amount of lanes from the database as the scraped bam file
                if len(bam.lanes.all()) != len(sequence_lanes):
                    print("Different number of lanes.")
                    continue

                # Check that all the lanes from the database bam file are the same as the scraped bam file
                for lane in bam.lanes.all():
                    if lane not in sequence_lanes:
                        print("Lane {} not in Sequence_lanes".format(vars(lane)))
                        add = False

                # Check the sizes
                if bam.bam_file.size != line.bytes:
                    different_size.append(line.path)
                    print("Size is different. Database: {} Scraped: {}".format(bam.bam_file.size, line.bytes))
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
                no_bams_found.append(line['path'])
                print ("No BamFiles found for Sequence: {} and Lanes {}.".format(dna_sequence, sequence_lanes))
                #TODO maybe create it here?
                continue

            # No examples of this edge case
            if len(bam_file) > 1:
                print(bam_file)
                print(line['path'])
                print("More than 1 Bamfile for sequence {} and lanes {}".format(dna_sequence.sample.sample_id, sequence_lanes))
                multiple_bams_found.append(line['path'])
                continue

            bam_file_resource = FileResource.objects.get(id=bam_file[0].bam_file_id)

            # Create the Bam instance
            bam_file_instance , created=FileInstance.objects.get_or_create(
                storage=storage,
                file_resource=bam_file_resource)

            bam_file_instance.filename_override = line['file']

            if created:
                bam_file_instance.save()

            # Create the Bam index Instance
            if not pd.isnull(line['index_file']):
                bai_file_resource = FileResource.objects.get(id=bam_file[0].bam_index_file_id)
                bai_file_instance, created = FileInstance.objects.get_or_create(
                    storage=storage,
                    file_resource=bai_file_resource)
                bai_file_instance.filename_override = line['index_file']
                if created:
                    bai_file_instance.save()

            added_to_tantalus.append(line)


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
    for line in added_to_tantalus:
        print line.library_type
    # print(added_to_tantalus)

if __name__ == '__main__':
    # bulk_bam = pd.read_csv('scrapers/bulk_bam.txt', sep='\t')
    # get_remote_metadata(bulk_bam)

    # Loop through files
    # df = pd.DataFrame.from_csv("scrapers/bulk_bam_metadata2.csv")
    # #
    # success = 0
    # fail = 0
    #
    # for (index, line) in df.iterrows():
    #     try:
    #         query_gsc_wgs_bam_library(line.library_id, line.sample_id)
    #     except:
    #         fail = fail + 1
    #         continue

    # print(fail)
    # print(success)

    # Load /share/lustre/archive files into tantalus
    load_into_tantalus()
