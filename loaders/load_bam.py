import argparse
import django
import paramiko
import re
from tantalus.colossus import *

django.setup()
from tantalus.models import *


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('bamfile', help='The bamfile')
    parser.add_argument('storage', choices=['gsc', 'rocks', 'shahlab'])
    parser.add_argument('--library')
    parser.add_argument('--sample_id')
    parser.add_argument('--lanes', nargs='*')
    parser.add_argument('--aligner')
    parser.add_argument('--reference_genome')
    return parser.parse_args()


def exec_command(cmd, client):
    stdin, stdout, stderr = client.exec_command(cmd)
    if stderr.channel.recv_exit_status() != 0:
        print stderr.read()
        raise Exception("ERROR on command: " + cmd)
    return stdout.read()


def find_lines(pattern, lines):
    return list(filter(lambda x: x.startswith(pattern), lines.splitlines(False)))


def find_word(tag, lines):
    tagged = []
    for line in lines:
        matched = re.match('.*{}([\w\.]+)\t?.*$'.format(tag), line)
        if matched:
            tagged.append(matched.group(1))
    return tagged


def get_library(header):
    library_lines = find_lines('@RG', header)
    library = find_word('LB:', library_lines)
    if len(set(library)) > 1:
        raise Exception('More than 1 library: {}'.format(set(library)))
    else:
        return library[0]


def get_sample(header):
    sample_lines = find_lines('@RG', header)
    sample = find_word('SM:', sample_lines)
    if len(set(sample)) > 1:
        raise Exception('More than 1 Sample: {}'.format(set(sample)))
    else:
        return sample[0]


def get_lanes(header):
    lane_lines = find_lines('@RG', header)
    lanes = find_word('PU:', lane_lines)
    return lanes


lengths = {197195432: 'MM9', 195471971: 'MM10', 249250621: 'HG19', 248956422: 'HG38', 247249719: 'HG18'}
def get_ref_genom(header):
    lines = find_lines('@SQ', header)
    reference_genome = find_word('AS:', lines)
    if len(set(reference_genome)) > 1:
        raise Exception('More than 1 reference genome')
    elif len(set(reference_genome)) == 1:
        return reference_genome[0]
    else:
        for line in lines:
            chr = find_word('SN', [line])
            if chr == '1':
                length = find_word('LN', [line])
                return lengths[int(length)]
    raise Exception('Cannot determine reference genome')


def _get_aligner_version_from_string(string, aligner):
    return re.match(".*{}_(\S*) .*".format(aligner), string).group(1)


def get_aligner(header):
    pg_lines = find_lines('@PG', header)
    aligner_list = []
    for line in pg_lines:
        command = re.match('.*CL:(.*)VN(\S*)', line)
        if not 'bwa' in command.group(1):
            continue
        aligner_list.append(command.group(1) + '_' + command.group(2) + ' ')
    # Aligner and version are separated by _ while different aligners are separated by spaces
    aligners = str(aligner_list)
    # For bamfiles with a Sambamba line
    if 'mem' in aligners and 'Sambamba' in aligners:
        return 'BWA-mem {} Alignment Sambamba'.format(_get_aligner_version_from_string(aligners, 'mem'))
    if 'mem' in aligners:
        return 'BWA-mem {} Alignment'.format(aligners, 'mem')
    raise Exception("Could not recognize the aligner in the samfile, please manually pass it in")


def read_header(args, client):
    header = exec_command('samtools view -H {}'.format(args.bamfile), client)

    if args.library is None:
        library = get_library(header)
    else:
        library = args.library

    if args.sample_id is None:
        sample_id = get_sample(header)
    else:
        sample_id = args.sample_id
        
    if args.lanes is None:
        lanes = get_lanes(header)
    else:
        lanes = args.lanes

    if args.reference_genome is None:
        reference_genome = get_ref_genom(header)
    else:
        reference_genome = args.reference_genome

    if args.aligner is None:
        aligner = get_aligner(header)
    else:
        aligner = args.aligner

    print('Library: {}\nSample: {}\nLanes: {}'.format(library, sample_id, lanes))
    return library, sample_id, lanes, reference_genome, aligner


# Gets creation time, size and looks for bai file
def get_metadata(args, client):
    # Creation Time
    stat = exec_command('stat {}'.format(args.bamfile), client)
    creation_time = stat.splitlines(False)[5][8:-8]
    size = int(re.match('^.*Size: (\d+).*$', stat.splitlines(False)[1]).group(1))

    # Check for bai file
    stat = exec_command('stat {}.bai'.format(args.bamfile), client)
    bai_time = stat.splitlines(False)[5][8:-8]
    bai_size = int(re.match('^.*Size: (\d+).*$', stat.splitlines(False)[1]).group(1))

    return creation_time, size, bai_time, bai_size

def main():
    args = get_args()

    client = paramiko.SSHClient()
    client.load_system_host_keys()
    # TODO CHANGE BEFORE MERGING IN
    if args.storage == 'rocks':
        client.connect(
            'beast.cluster.bccrc.ca',
            username='tchan'
        )

    if args.storage == 'gsc':
        client.connect(
            '10.9.208.161',
            username='tichan'
        )

    if args.storage == 'shahlab':
        client.connect(
            '10.9.208.161',
            username='tichan'
        )

    storage = ServerStorage.objects.get(name=args.storage)

    library, sample, lanes, ref_genome, aligner = read_header(args, client)
    creation_time, size, bai_time, bai_size = get_metadata(args, client)
    library = DNALibrary.objects.get(library_id=library)
    sample = Sample.objects.get(sample_id=sample)
    sequence_lanes = []

    for lane in lanes:
        if len(lane.split('.')) > 1:
            sequence_lanes.append(SequenceLane.objects.get(
                flowcell_id=lane.split('.')[0],
                lane_number=lane.split('.')[1])
            )
        else:
            sequence_lanes.append(SequenceLane.objects.get(
                flowcell_id=lane)
            )

    with django.db.transaction.atomic():
        read_groups = []
        for lane in sequence_lanes:
            read_group, created = ReadGroup.objects.get_or_create(
                sample_id=sample,
                dna_library=library,
                sequence_lane=lane
            )
            read_groups.append(read_group)

        # FOR NEW FILES
        bam_resource, created = FileResource.objects.get_or_create(
            created=creation_time,
            file_type='BAM',
            filename=args.bamfile[len(storage.storage_directory)-1:],
            size=size,
            compression=FileResource.UNCOMPRESSED
        )
        if created:
            bam_resource.read_groups = read_groups
            bam_resource.save()

        bai_resource, created = FileResource.objects.get_or_create(
            created=bai_time,
            file_type='BAI',
            filename=args.bamfile[len(storage.storage_directory)-1:] + '.bai',
            size=bai_size
        )
        if created:
            bai_resource.read_groups = read_groups
            bai_resource.save()

        bamfile, created = BamFile.objects.get_or_create(
            reference_genome=ref_genome,
            aligner=aligner,
            bam_file=bam_resource,
            bam_index_file=bai_resource,
        )

        bam_instance, created = FileInstance.objects.get_or_create(
            file_resource=bam_resource,
            storage=storage
        )

        bai_instance, created = FileInstance.objects.get_or_create(
            file_resource=bai_resource,
            storage=storage
        )

        print('Bamfile: {}\nBam FileResource: {}\nBam FileInstance: {}\nBai FileResource: {}\n Bai FileInstance: {}'.format(
            bamfile.id, bam_resource.id, bam_instance.id, bai_resource.id, bai_instance.id
        ))


if __name__ == '__main__':
    main()
