#!/usr/bin/env python
"""This script converts SpECs on Shahlab to BAMs on Shahlab.

To be clear, this script *must* be run on Shahlab. The main reason for
this is that the program spec2bam requires a license and is only
available on Shahlab and GSC; since write access is currently prohibited
on GSC, it makes sense to use the binary on Shahlab.

The JSON arguments this script expects is 'tags', which is a list of
strings containing tag names attached to SpEC files to be decompressed.
"""

from __future__ import print_function
import datetime
import json
import os
import subprocess
import sys
import django
from django.db import transaction

# Allow access to Tantalus DB
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tantalus.settings")
django.setup()

# Import Tantalus stuff now that we have access
from tantalus.backend.file_transfer_utils import get_file_md5
from tantalus.models import BamFile, FileInstance, FileResource, Storage


# Useful variables
SHAHLAB_HOSTNAME = 'node0515'
SHAHLAB_SPEC2BAM_BINARY_PATH = r'/gsc/software/linux-x86_64-centos6'

# This dictionary maps a (Tantalus) BamFile's reference genome field to
# the path of the reference genome FASTA files on Shahlab. We only care
# about the reference genomes that BamFile cares about (currently HG18
# and HG19).
HUMAN_REFERENCE_GENOMES_MAP = {
    'hg18': r'/shahlab/pipelines/reference/gsc_hg18.fa',
    'hg19': r'/shahlab/pipelines/reference/gsc_hg19a.fa',}


def spec_to_bam(bamfile):
    """Decompresses a SpEC compressed BamFile.

    Registers the new uncompressed file in the database.
    """
    # Ensure the BamFile is SpEC compressed
    assert bamfile.bam_file.compression == FileResource.SPEC

    # Get path of uncompressed BAM: remove '.spec' but path otherwise is
    # the same
    output_bam_path = bamfile.bam_file.filename[:-5]

    # Convert the SpEC to a BAM
    command = [SHAHLAB_SPEC2BAM_BINARY_PATH,
               '--in',
               bamfile.bam_file.filename,
               '--ref',
               HUMAN_REFERENCE_GENOMES_MAP[bamfile.reference_genome],
               '--out',
               output_bam_path,
              ]
    subprocess.check_call(command)

    # Create the new BamFile, starting with the file resource first
    new_bam_file_resource = FileResource(
        md5=get_file_md5(output_bam_path),
        size=os.path.getsize(output_bam_path),
        created=datetime.datetime.now(),
        file_type=FileResource.BAM,
        compression=FileResource.UNCOMPRESSED,
        filename=output_bam_path)
    new_bam_file_resource.save()

    # Now the BamFile
    new_bam_file = BamFile(
        reference_genome=bamfile.reference_genome,
        aligner=bamfile.aligner,
        bam_file=new_bam_file_resource,)
    new_bam_file.save()

    # Now the file instance
    new_bam_file_instance = FileInstance(
        storage=Storage.objects.get(name='shahlab'),
        file_resource=new_bam_file_resource,)
    new_bam_file_instance.save()


@transaction.atomic
def main():
    """Main script for SpEC to BAM conversion."""
    # Make sure we're on Shahlab
    if os.environ['HOSTNAME'] != SHAHLAB_HOSTNAME:
        print("Must run this script on GSC!", file=sys.stderr)
        sys.exit(1)

    # Parse the JSON args
    json_args = sys.argv[1]
    args_dict = json.loads(json_args)

    # Get the BamFile rows that contains the SpEC files
    tag_names = args_dict['tags']
    bams = BamFile.objects.filter(tags__name__in=tag_names)

    # Process each BamFile
    for bam in bams:
        spec_to_bam(bam)


if __name__ == '__main__':
    # Run the script
    main()
