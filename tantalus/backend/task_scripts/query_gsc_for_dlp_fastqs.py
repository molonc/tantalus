import os
import subprocess
import django

from tantalus.backend.task_scripts.utils import *
from tantalus.models import GscDlpPairedFastqQuery
import tantalus.backend.serializers


def query_gsc_dlp_paired_fastqs(query_info, temp_directory):
    script = os.path.join(
        django.conf.settings.BASE_DIR,
        'tantalus', 'backend', 'scripts',
        'query_gsc_for_dlp_fastqs.py')

    json_data_filename = os.path.join(
        temp_directory, 'new_data.json')

    cmd = ['python', '-u', script]
    cmd.append(json_data_filename)
    cmd.append(query_info.dlp_library_id)
    cmd.append(query_info.gsc_library_id)

    subprocess.check_call(cmd)
    
    tantalus.backend.serializers.read_models(json_data_filename)


if __name__ == '__main__':
    args = parse_args()
    run_task(args['primary_key'], GscDlpPairedFastqQuery, query_gsc_dlp_paired_fastqs)
