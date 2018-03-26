from tantalus.backend.scripts.utils import *
from tantalus.backend.gsc_queries import query_gsc_dlp_paired_fastqs
from tantalus.models import GscDlpPairedFastqQuery


if __name__ == '__main__':
    args = utils.parse_args()
    utils.run_task(args['primary_key'], GscDlpPairedFastqQuery, query_gsc_dlp_paired_fastqs)
