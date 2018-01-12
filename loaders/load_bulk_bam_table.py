from datetime import datetime
import os
import sys
import string
import pandas as pd
import django
import paramiko
import re
import ast


sys.path.append('./')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tantalus.settings')
django.setup()
DIRECTORY_TO_STRIP = "/share/lustre/archive/single_cell_indexing/HiSeq/"

import tantalus.models
from tantalus.gsc_queries import *


def _read_chrom_lengths(file, name, dict):
    for line in file.readlines():
        chr, len = line.strip().split('\t')
        len = int(len)
        if chr == 'chrM':
            continue
        if dict.has_key((chr, len)):
            raise Exception("Chrom length not unique" + str((chr, len)))
        dict[(chr, len)] = name


def read_lengths():
    lengths = {}
    with open('scrapers/chromlengths_19.txt', 'r') as f:
        _read_chrom_lengths(f, 'HG19', lengths)

    with open('scrapers/chromlengths_18.txt', 'r') as f:
        _read_chrom_lengths(f, 'HG18', lengths)

    lengths[('chr1', 197195432)] = 'MM9'
    lengths[('chr1', 195471971)] = 'MM10'

    return lengths


chrom_lengths = read_lengths()


def reverse_complement(sequence):
    return sequence[::-1].translate(string.maketrans('ACTGactg','TGACtgac'))


# def get_sam_header_information(file_to_bam):
#     #TODO: ask andrew for help
    # libraries = pd.HDFStore('loaders/single_cell_hiseq_fastq_metadata.h5', 'r')['/metadata']['id']
    # return libraries


def get_or_create_scraped_samples(df):
    # df = pd.DataFrame.from_csv('scrapers/bulk_bam.txt', sep='\t', index_col=None)
    samples = set(df['sample_id'])
    for s in samples:
        tantalus.models.Sample.objects.get_or_create(
            sample_id=s
        )


def get_or_create_scraped_dna_library(bulk_bam):
    df = pd.DataFrame.from_csv('scrapers/bulk_bam.txt', sep='\t', index_col=None)
    libs = set(df['library_id'])
    for lib in libs:
        tantalus.models.DNALibrary.objects.get_or_create(
            library_id=lib,
            #TODO: ask andrew what to fill in for the other fields of DNA Library..
        )


def get_genome_version(genome):
    if '/' in genome:
        return genome.split('/')[0]


def determine_genome_by_length(sequence_name, length):
    try:
        return chrom_lengths[(sequence_name, length)]
    except KeyError:
        raise Exception("Could not determine chromosome for length: " + sequence_name + ' ' + str(length))


def standardize_names(name):
    match = re.match('^[\dMXYT]+$', name)
    if match:
        return 'chr' + name
    return name


def get_reference_genome_for_line(line):
    # Check if genome is specified
    # name = re.match('^.*AS:([\w/]+)\t?.*$', line)
    # if name:
    #     genome = get_genome_version(name.group(1))
    # If not, then determine it based on chromosone lengths
    # else:
    length = re.match('^.*LN:(\d+)\t?.*$', line)
    if length:
        sequence_name = standardize_names(re.match('^.*SN:([^\t.]*)\t.*', line).group(1))
        # Ignore chromosome M
        if sequence_name == 'chrM' or sequence_name == 'chrMT':
            return 'M'
        genome = determine_genome_by_length(sequence_name, int(length.group(1)))
    return genome


def find_lines(pattern, lines):
    return list(filter(lambda x: x.startswith(pattern), lines.splitlines(False)))


def get_reference_genome(out):
    ReferenceSequences = find_lines('@SQ', out)
    if len(ReferenceSequences) == 0:
        return 'ignore'
    chr1 = list(filter(lambda x: 'SN:1\t' in x or 'SN:chr1\t' in x, ReferenceSequences))[0]
    return get_reference_genome_for_line(chr1)
    # ReferenceSequences = find_lines('@SQ', out)
    # genome = list(set(map(lambda x: get_reference_genome_for_line(x), ReferenceSequences)))
    # if 'M' in genome:
    #     genome.remove('M')
    # if len(genome) == 1:
    #     return genome[0]
    # elif len(genome) == 0:
    #     return "None found"
    # else:
    #     return "More than 1"


def get_aligner(out):
    aligner_lines = find_lines('@PG', out)
    # Check if program name exists
    aligner = ""
    version = ""

    # Look for program name first
    for line in aligner_lines:
        match = re.match('.*(PN:)\t?.*$', line)
        if match:
            if 'bwa' in match.group(1):
                aligner = match.group(1)[3:]


    # If it can't find program name then look for CL
    if aligner == "":
        for line in aligner_lines:
            match = re.match('.*(CL:bwa.*)\t.*$', line)
            if match:
                aligner = match.group(1)[3:]
                match = re.match('.*(VN:)\t.*', line)
                if match:
                    version = match.group(1)[3:]
    return aligner, version


def get_lanes(out):
    lanes = []
    lane_lines = find_lines('@RG', out)
    for line in lane_lines:
        technology = re.match('.*PL:(\w+)\t?.*$', line)
        if technology:
            if technology.group(1) == "illumina":
                full_flowcell = re.match('.*PU:(\w+).(\d)', line)
                if full_flowcell is None:
                    return "ignore"
                flowcell_id = full_flowcell.group(1)
                lane_number = full_flowcell.group(2)
                lanes.append((flowcell_id, lane_number))
            else:
                return "ignore"
    return lanes


def get_center(out):
    center_lines = find_lines('@RG', out)
    sequencing_center = []
    for line in center_lines:
        center = re.match('.*CN:(\w+)\t?.*$', line)
        if center:
            sequencing_center.append(center.group(1))

    return list(set(sequencing_center))


def get_library_from_header(out):
    library_lines = find_lines('@RG', out)
    library = []
    for line in library_lines:
        lib = re.match('.*LB(\w+)\t?.*$', line)
        if lib: library.append(lib.group(1))
    return library


def get_remote_metadata(bulk_bam):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.connect(
        'beast.cluster.bccrc.ca',
        username='tchan'
    )

    df = pd.DataFrame.from_csv("scrapers/bulk_bam_metadata.csv")

    # df = pd.DataFrame(columns=['sample_id', 'library_type', 'library_id', 'file_type', 'file', 'bytes', 'path', 'index_file', 'bai_bytes', 'notes',
    #                            'reference_genome', 'aligner', 'lanes'])
    for idx, line in df.iterrows():
        if 'TASK' in line.path:
            continue
        stdin, stdout, stderr = client.exec_command("samtools view -H {}".format(line.path))
        if stderr.channel.recv_exit_status() != 0:
            print stderr.read()
            raise Exception("Non zero exit on line {}".format(line))

        sam_header = stdout.read()

        # Get Genome
        # reference_genome = get_reference_genome(sam_header)
        # if reference_genome == "ignore":
        #     continue
        # if reference_genome == "None found" or reference_genome == "More than 1":
        #     raise Exception(reference_genome)
        #
        # # Get Aligner
        # aligner, version = get_aligner(sam_header)
        #
        # # Get Lanes
        # lanes = get_lanes(sam_header)
        # if lanes == "ignore":
        #     continue

        # Get Sequencing Center
        center = get_center(sam_header)

        # See what the file says is it's libary
        file_library = get_library_from_header(sam_header)

        # Get creation time
        # stdin, stdout, stderr = client.exec_command("stat {}".format(line.path))
        #
        # Modify = stdout.readlines()[5][:-8]
        #
        # line['created'] = Modify

        # Check for bai file
        # stdin, stdout, stderr = client.exec_command("stat {}.bai".format(line.path))
        # if stderr.channel.recv_exit_status() != 0:
        #     print stderr.read()
        #     raise Exception("Non zero exit on line {}".format(line.path + '.bai'))

        # if len(stderr.read()) == 0:
        #     line['index_file'] = line.path + '.bai'
        #     # line['bai_bytes'] = int(full_ll.split('\t')[0])
        #     out = stdout.readlines()[1]
        #     line['bai_bytes'] = int(re.match('^.*Size: (\d+).*$', out).group(1))
        #
        #     stdin, stdout, stderr = client.exec_command("stat {}.bai".format(line.path))
        #
        #     Modify = stdout.readlines()[5][:-8]
        #
        #     line['bai-created'] = Modify
        # else:
        #     line['index_file'] = "N/A"
        #
        # line['reference_genome'] = reference_genome
        # line['aligner'] = aligner
        # line['aligner_version'] = version
        # line['lanes'] = lanes
        line['center'] = center
        line['file_libary'] = file_library

        df = df.append(line)
    df.to_csv('scrapers/bulk_bam_metadata2.csv')


library = {'illumina_wgss': 'WGS', 'illumina_wtss': 'RNASEQ', 'illumina_exoncapture': 'EXOME', 'exon_capture': 'EXOME',
           'illumina_amplicon': "AMPLICON", 'illumina_chip': 'CHIP', 'illumina_bisulfite': 'BISULFITE'}


def translate_library_type(type):
    return library[type]


def load_into_tantalus():
    df = pd.DataFrame.from_csv("scrapers/bulk_bam_metadata2.csv")

    storage = tantalus.models.Storage.objects.get(name="rocks")

    for index, line in df.iterrows():

        # These ones are skipped
        if line['library_id'] == "abi_solid" or line['library_id'] == 'illumina_mirna':
            continue

        sample = line['sample_id']
        sample, created = tantalus.models.Sample.objects.get_or_create(sample_id=sample)
        if created:
            sample.save()

        library_id = line['library_id']
        library_type = translate_library_type(line['library_type'])
        index_format = 'N'

        library, created = tantalus.models.DNALibrary.objects.get_or_create(
            library_id=library_id,
            library_type=library_type,
            index_format=index_format)
        if created:
            library.save()

        sequence, created = tantalus.models.DNASequences.objects.get_or_create(
            index_sequence=None,
            dna_library=library,
            sample=sample)
        if created:
            sequence.save()

        if len(line['lanes']) == 0:
            sequencelane, created = tantalus.models.SequenceLane.objects.get_or_create(
                dna_library=library,
                flowcell_id=None,
                lane_number=None,
                sequencing_centre='Unknown',
                sequencing_library_id=library_id,
                sequencing_instrument='Unknown')
            if created:
                sequencelane.save()
        else:
            for lane in ast.literal_eval(line['lanes']):
                sequencelane, created = tantalus.models.SequenceLane.objects.get_or_create(
                    dna_library=library,
                    flowcell_id=lane[0],
                    lane_number=lane[1],
                    sequencing_centre='Unknown',
                    sequencing_library_id=library_id,
                    sequencing_instrument='Unknown')

                if created:
                    sequencelane.save()



        # Create File Resource. Get md5 later or something. Ask if I should ll the file to get created time
        # Ask if all these files also have a bai file
        bam_file_resource, created = tantalus.models.FileResource.objects.get_or_create(
            size=line['bytes'],
            file_type='BAM',
            compression='UNCOMPRESSED',
            read_end=None,
            filename=line['file'],
            created=datetime.strptime(line['created'], 'Modify: %Y-%m-%d %H:%M:%S.%f00'))
        if created:
            bam_file_resource.save()

        if not pd.isnull(line['index_file']):
            bai_file_resource, created = tantalus.models.FileResource.objects.get_or_create(
                size=int(line['bai_bytes']),
                file_type='BAI',
                read_end=None,
                compression='UNCOMPRESSED',
                filename=line['index_file'].split('/')[-1],
                created=datetime.strptime(line['bai-created'],'Modify: %Y-%m-%d %H:%M:%S.%f00'))
            if created:
                bai_file_resource.save()

        # Create File Instance

        bam_file_instance, created = tantalus.models.FileInstance.objects.get_or_create(
            storage=storage,
                                                                                        file_resource=bam_file_resource,
                                                                                        filename_override=line[
                                                                                            'path'].strip(
                                                                                            storage.get_filepath(bam_file_resource)))
        if created:
            bam_file_instance.save()

        if not pd.isnull(line['index_file']):
            bai_file_instance, created = tantalus.models.FileInstance.objects.get_or_create(storage=storage,
                                                                                            file_resource=bai_file_resource,
                                                                                            filename_override=line[
                                                                                                'index_file'].strip(
                                                                                                storage.get_filepath(bai_file_resource)))
            if created:
                bai_file_instance.save()

        bamfile, created = tantalus.models.BamFile.objects.get_or_create(reference_genome=line['reference_genome'],
                                                                         aligner=line['aligner'],
                                                                         bam_file=bam_file_resource,
                                                                         bam_index_file=bai_file_resource,
                                                                         )
        if created:
            bamfile.save()


if __name__ == '__main__':
    # make calls to the function here when you run the script to load in data
    # bulk_bam = pd.read_csv('scrapers/bulk_bam.txt', sep='\t')
    # get_remote_metadata(bulk_bam)

    df = pd.DataFrame.from_csv("scrapers/bulk_bam_metadata2.csv")

    samples = list(df['sample_id'].unique())
    for sample in samples:
        query_gsc_wgs_bams(sample)

    # load_into_tantalus()
