from tantalus.backend.scripts.utils import *
from tantalus.backend.import_brc_fastqs import load_brc_fastqs
from tantalus.models import BRCFastqImport


if __name__ == '__main__':
    args = utils.parse_args()
    utils.run_task(args['primary_key'], BRCFastqImport, load_brc_fastqs)
