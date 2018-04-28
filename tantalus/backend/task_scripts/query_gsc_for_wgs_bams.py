import django

from tantalus.backend.scripts.utils import *
from tantalus.models import GscWgsBamQuery
import tantalus.backend.serializers


def query_gsc_wgs_bams(query_info, temp_directory):
    script = os.path.join(
        django.conf.settings.BASE_DIR,
        'tantalus', 'backend', 'scripts',
        'query_gsc_for_wgs_bams.py')

    json_data_filename = os.path.join(
        temp_directory, 'new_data.json')

    cmd = ['python', '-u', script]
    cmd.append('--library_ids')
    cmd.extend(query_info.library_ids)

    cmd.append('--json_data')
    cmd.append(json_data_filename)

    task = subprocess.Popen(cmd)
    
    tantalus.backend.serializers.read_models(json_data_filename)


if __name__ == '__main__':
    args = parse_args()
    run_task(args['primary_key'], GscWgsBamQuery, query_gsc_wgs_bams)
