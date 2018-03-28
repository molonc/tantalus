from tantalus.backend.scripts.utils import *
from tantalus.backend.file_transfer_utils import transfer_files
from tantalus.models import FileTransfer


if __name__ == '__main__':
    args = parse_args()
    run_task(args['primary_key'], FileTransfer, transfer_files)
