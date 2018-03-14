import os
import subprocess
import django

from tantalus.backend.task_scripts.utils import *
from tantalus.models import ImportDlpBam
import tantalus.backend.serializers


def import_dlp_realign_bams_wrapper(query_info, temp_directory):
    script = os.path.join(
        django.conf.settings.BASE_DIR,
        'tantalus', 'backend', 'scripts',
        'dlp_bam_import.py')

    json_data_filename = os.path.join(
        temp_directory, 'new_data.json')

    cmd = ['python', '-u', script]
    cmd.append(json_data_filename)
    cmd.append(query_info.storage.name)
    cmd.append(query_info.storage.storage_type)
    cmd.extend(query_info.bam_paths)
    if query_info.storage.storage_type == 'blob':
        os.environ['AZURE_STORAGE_ACCOUNT'] = query_info.storage.azureblobstorage.storage_account
        os.environ['AZURE_STORAGE_KEY'] = query_info.storage.azureblobstorage.credentials.storage_key
        os.environ['COLOSSUS_API_URL'] = django.conf.settings.COLOSSUS_API_URL
        cmd.append('--blob_container_name')
        cmd.append(query_info.storage.azureblobstorage.storage_container)

    subprocess.check_call(cmd)
    
    tantalus.backend.serializers.read_models(json_data_filename)


if __name__ == '__main__':
    args = parse_args()
    run_task(args['primary_key'], ImportDlpBam, import_dlp_realign_bams_wrapper)
