from tantalus.backend.task_scripts.utils import *
from tantalus.backend.file_transfer_utils import check_or_update_md5
from tantalus.models import CheckMD5


if __name__ == '__main__':
    args = parse_args()
    run_task(args['primary_key'], CheckMD5, check_or_update_md5)
