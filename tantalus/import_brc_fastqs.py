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


def create_Sample(sample_id):
    sample, created = tantalus.models.Sample.objects.get_or_create(
        sample_id=sample_id,
    )
    if created:
        sample.save()
    return sample


def create_DNALibrary(library_id):
    dna_library, created = tantalus.models.DNALibrary.objects.get_or_create(
        library_id=library_id,
        index_format=BRC_INDEX_FORMAT,
        library_type=BRC_LIBRARY_TYPE,
    )
    if created:
        dna_library.save()
    return dna_library


def create_SequenceLane(dna_library, flowcell_id, lane_number, sequencing_library_id):
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


def create_DNASequences(dna_library, sample, index_sequence):
    dna_sequence, created = tantalus.models.DNASequences.objects.get_or_create(
        dna_library=dna_library,
        sample=sample,
        index_sequence=index_sequence,
    )
    if created:
        dna_sequence.save()
    return dna_sequence


def create_FileResource_and_FileInstance(output_dir, filepath, read_end, new_files, storage):
    abspath = os.path.join(storage.get_storage_directory(), filepath)
    file_resource, created = tantalus.models.FileResource.objects.get_or_create(
        size=os.path.getsize(abspath),
        created=pd.Timestamp(time.ctime(os.path.getmtime(abspath)), tz='Canada/Pacific'),
        file_type=tantalus.models.FileResource.FQ,
        read_end=read_end,
        compression=tantalus.models.FileResource.GZIP,
        filename=filepath
    )
    if created:
        file_resource.save()

    file_instance, created = tantalus.models.FileInstance.objects.get_or_create(
        storage=storage,
        file_resource=file_resource,
        filename_override=""
    )
    if created:
        file_instance.save()
        new_files.append(file_instance)

    return file_resource, file_instance


def create_PairedEndFastqFiles(reads_1_file, reads_2_file, dna_sequence, lane):
    Paired_End_Fastq_Files, created = tantalus.models.PairedEndFastqFiles.objects.get_or_create(
        reads_1_file=reads_1_file,
        reads_2_file=reads_2_file,
        dna_sequences=dna_sequence
    )
    if created:
        Paired_End_Fastq_Files.save()

    Paired_End_Fastq_Files.lanes.add(lane)
    Paired_End_Fastq_Files.save()


def get_files_in_output(output_dir):
    fastqs = list(filter(lambda x: ".fastq.gz" in x, os.listdir(output_dir)))
    determined = list(filter(lambda x: "Undetermined" not in x, fastqs))
    return determined


def query_colossus_dlp_cell_info(library_id):
    library_url = '{}library/?pool_id={}'.format(
        django.conf.settings.COLOSSUS_API_URL,
        library_id)

    r = requests.get(library_url)

    if r.status_code != 200:
        raise Exception('Returned {}: {}'.format(r.status_code, r.reason))

    if len(r.json()) == 0:
        raise Exception('No entries for library {}'.format(library_id))

    if len(r.json()) > 1:
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


def put_into_tantalus(file_df, output_dir, storage):
    """Create the rows in the table for the fastq files

    """
    with django.db.transaction.atomic():
        new_files = []
        paired_files = collections.defaultdict(dict)
        storage = tantalus.models.ServerStorage.objects.get(name=storage)
        storage_path = storage.get_storage_directory()
        for index, fastq_file in file_df.iterrows():
            sample_id = fastq_file["sample_id"]
            chip_id = fastq_file["chip_id"]
            flowcell_id = fastq_file["flowcell_id"]
            lane_number = '' # null is no empty string for this field
            index_sequence = fastq_file["index_sequence"]
            filename = fastq_file["filename"]
            filepath = os.path.join(output_dir, filename)
            # Get the relative filepath
            filepath = filepath.replace(storage_path + '/', '')
            read_end = int(fastq_file["read_end"][1])
            row = fastq_file["row"]
            col = fastq_file["column"]
            lane = fastq_file["lane"]

            Sample = create_Sample(sample_id=sample_id)

            DNA_Library = create_DNALibrary(library_id=chip_id)

            SequenceLane = create_SequenceLane(
                dna_library=DNA_Library,
                flowcell_id=flowcell_id,
                lane_number=lane_number,
                sequencing_library_id=chip_id,
            )

            DNA_Sequence = create_DNASequences(
                dna_library=DNA_Library,
                sample=Sample,
                index_sequence=index_sequence,
            )

            File_Resource, File_Instance = create_FileResource_and_FileInstance(
                output_dir,
                filepath=filepath,
                read_end=read_end,
                new_files=new_files,
                storage=storage,
            )

            fastq_id = (row, col, lane)

            if read_end in paired_files[fastq_id]:
                raise Exception("Duplicate fastq end {} for {}".format(read_end, fastq_id))
            else:
                paired_files[fastq_id][read_end] = {
                    "fastq_file":File_Resource,
                    "dna_sequences":DNA_Sequence,
                    "sequence_lane": SequenceLane
                }

        for fastq_id, paired_file in paired_files.iteritems():
            if set(paired_file.keys()) != set([1, 2]):
                raise Exception('expected read end 1, 2 for {}, got {}'.format(fastq_id, paired_file.keys()))

            if paired_file[1]['dna_sequences'].id != paired_file[2]['dna_sequences'].id:
                raise Exception('expected same dna sequences for {}'.format(fastq_id))

            if paired_file[1]['sequence_lane'].id != paired_file[2]['sequence_lane'].id:
                raise Exception('expected same lane for {}'.format(fastq_id))

            create_PairedEndFastqFiles(reads_1_file=paired_file[1]["fastq_file"],
                                       reads_2_file=paired_file[2]["fastq_file"],
                                       dna_sequence=paired_file[1]["dna_sequences"],
                                       lane=paired_file[1]["sequence_lane"])

        django.db.transaction.on_commit(lambda: tantalus.utils.start_md5_checks(new_files))


def check_lane_demultiplexing(file):
    return re.match("^[a-zA-Z0-9]+-A\\d+[a-zA-Z0-9]+-R\\d\\d?-C\\d\\d?_S\\d+_L00\\d_R[12]_001.fastq.gz$", file)


def get_file_info(fastq_files, flowcell_id):
    # ASSUMPTION: only 1 chip_id
    chip_id = list(set(map(lambda x: x.split('-')[1], fastq_files)))[0]
    cell_info = query_colossus_dlp_cell_info(chip_id)

    # Checks only once if lane is demultiplexed, if they are mixed, then an error will be thrown later
    demuliplex = check_lane_demultiplexing(fastq_files[0])

    info = []
    for filename in fastq_files:
        if demuliplex:
            ignored_sample, chip, row, rest = filename.split('-')
            col, ignore, lane, read, ignored, = rest.split('_')
        else:
            ignored_sample, chip, row, rest = filename.split('-')
            col, ignore, read, ignored, = rest.split('_')
            lane = 0

        row_number = int(row[1:])
        col_number = int(col[1:])

        index_sequence = cell_info[row_number, col_number]["index_sequence"]
        sample = cell_info[row_number, col_number]["sample_id"]

        info.append([filename, sample, chip, row, col, read, index_sequence, lane])

    file_df = pd.DataFrame(info, columns=("filename", "sample_id", "chip_id", "row", "column", "read_end", "index_sequence", "lane"))

    chip_id = file_df["chip_id"].unique()
    if len(chip_id) > 1:
        raise Exception("More than 1 chip_id: ".format(chip_id))
    chip_id = chip_id[0]

    file_df["flowcell_id"] = flowcell_id

    return file_df


def check_output_dir_and_get_files(import_brc_fastqs):
    # Check for .. in file path
    if ".." in import_brc_fastqs.output_dir:
        raise Exception("Invalid path for output_dir. \'..\' detected")
    # Check that output_dir is actually in storage
    if not import_brc_fastqs.output_dir.startswith(import_brc_fastqs.storage.get_storage_directory()):
        raise Exception("Invalid path for output_dir. {} doesn't seem to be in the specified storage".format(import_brc_fastqs.output_dir))
    # Check that path is valid.
    if not os.path.isdir(import_brc_fastqs.output_dir):
        raise Exception("output directory {} not a directory".format(import_brc_fastqs.output_dir))
    # Check that the path actually has fastq files
    files = get_files_in_output(import_brc_fastqs.output_dir)
    if len(files) == 0:
        raise Exception("no fastq files in output directory {}".format(import_brc_fastqs.output_dir))
    return files


def load_brc_fastqs(import_brc_fastqs):
    fastq_files = check_output_dir_and_get_files(import_brc_fastqs)
    file_df = get_file_info(fastq_files, import_brc_fastqs.flowcell_id)
    put_into_tantalus(file_df, import_brc_fastqs.output_dir, import_brc_fastqs.storage)


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
