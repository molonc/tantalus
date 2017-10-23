import json
import os
import requests
import django
import time
import pandas as pd

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tantalus.settings')
    django.setup()

import tantalus.models
import tantalus.tasks

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


bam_path_template = '{data_path}/{library_name}_{num_lanes}_lanes_dupsFlagged.bam'


wgs_protocol_ids = (
    12,
    136,
    140,
    123,
)


solexa_run_type_map = {
    'Paired': tantalus.models.SequenceLane.PAIRED}


class MissingFileError(Exception):
    pass


def start_md5_checks(file_instances):
    for file_instance in file_instances:
        md5_check = tantalus.models.MD5Check(
            file_instance=file_instance
        )
        md5_check.save()

        tantalus.tasks.check_md5_task.apply_async(args=(md5_check.id,), queue=file_instance.storage.get_md5_queue_name())


def query_gsc_wgs_bams(sample_id):
    sample = tantalus.models.Sample.objects.get(sample_id=sample_id)
    storage = tantalus.models.ServerStorage.objects.get(name='gsc')

    # ASSUMPTION: GSC stored files are pathed from root
    assert storage.storage_directory == '/'

    gsc_api = GSCAPI()

    library_infos = gsc_api.query('library?external_identifier={}'.format(sample_id))

    if 'status' in library_infos and library_infos['status'] == 'error':
        raise Exception(library_infos['errors'])

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

                bam_path = bam_path_template.format(
                    data_path=data_path,
                    library_name=library_name,
                    num_lanes=num_lanes)
                bai_path = bam_path + '.bai'

                if not os.path.exists(bam_path):
                    raise MissingFileError(bam_path)

                if not os.path.exists(bai_path):
                    raise MissingFileError(bai_path)

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
                    sequencing_instrument = libcore['libcore']['run']['machine']
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

        django.db.transaction.on_commit(lambda: start_md5_checks(new_file_instances))


if __name__ == '__main__':
    query_gsc_wgs_bams('SA820G')


