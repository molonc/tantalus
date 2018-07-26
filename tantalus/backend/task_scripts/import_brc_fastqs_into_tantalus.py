import os
import subprocess
import django

from tantalus.backend.task_scripts.utils import *
from tantalus.models import BRCFastqImport
import tantalus.backend.serializers


def load_brc_fastqs(query_info, temp_directory):
    script = os.path.join(
        django.conf.settings.BASE_DIR,
        'tantalus', 'backend', 'scripts',
        'dlp_bcl_fastq_import.py')

    json_data_filename = os.path.join(
        temp_directory, 'new_data.json')

    cmd = ['python', '-u', script]
    cmd.append(json_data_filename)
    cmd.append(query_info.flowcell_id)
    cmd.append(query_info.storage.name)
    cmd.append(query_info.storage.storage_directory)
    cmd.append(query_info.output_dir)

    subprocess.check_call(cmd)
    
    tantalus.backend.serializers.read_models(json_data_filename)


if __name__ == '__main__':
    args = parse_args()
    run_task(args['primary_key'], BRCFastqImport, load_brc_fastqs)
