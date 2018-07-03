#!/usr/bin/env python
"""This script converts SpECs on Shahlab to BAMs on Shahlab.

To be clear, this script *must* be run on Shahlab. The main reason for
this is that the program spec2bam requires a license and is only
available on Shahlab and GSC; since write access is currently prohibited
on GSC, it makes sense to use the binary on Shahlab.

The JSON arguments this script expects is 'tags', which is a list of
strings containing tag names attached to Tantalus BamFiles that have
SpEC FileInstances on Shahlab to be decompressed.
"""

from __future__ import print_function
import json
import logging
import os
import re
import socket
import subprocess
import sys
import django
from django.db import transaction
from django.utils import timezone

# Allow access to Tantalus DB
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tantalus.settings")
django.setup()

# Import Tantalus stuff now that we have access
from tantalus.backend.file_transfer_utils import get_file_md5
from tantalus.models import BamFile, FileInstance, FileResource, Storage


# Logging config (it will print to console by default)
logging.basicConfig(format='%(levelname)s:%(message)s',
                    level=logging.DEBUG)

# Useful Shahlab-specific variables
SHAHLAB_TANTALUS_SERVER_NAME = 'shahlab'
SHAHLAB_HOSTNAME = 'node0515'
SHAHLAB_SPEC2BAM_BINARY_PATH = r'/gsc/software/linux-x86_64-centos6/spec-1.3.2/spec2bam'

# This dictionary maps a (Tantalus) BamFile's reference genome field to
# the path of the reference genome FASTA files on Shahlab. We only care
# about the reference genomes that BamFile cares about (currently HG18
# and HG19).
HUMAN_REFERENCE_GENOMES_MAP = {
    'hg18': r'/shahlab/pipelines/reference/gsc_hg18.fa',
    'hg19': r'/shahlab/pipelines/reference/gsc_hg19a.fa',}

# These are regular expressions for identifying which human reference
# genome to use. See https://en.wikipedia.org/wiki/Reference_genome for
# more details on the common standards and how they relate to each
# other. All of these should be run with a case-insensitive regex
# matcher.
HUMAN_REFERENCE_GENOMES_REGEX_MAP = {
    'hg18': [r'hg[-_ ]?18',                 # hg18
             r'ncbi[-_ ]?build[-_ ]?36.1',  # NCBI-Build-36.1
            ],
    'hg19': [r'hg[-_ ]?19',                 # hg19
             r'grc[-_ ]?h[-_ ]?37',         # grch37
            ],}


class BadReferenceGenomeError(Exception):
    pass


def get_uncompressed_bam_path(spec_path):
    """Get path of corresponding BAM file given a SpEC path.

    Get path of uncompressed BAM: remove '.spec' but path otherwise is
    the same.
    """
    return spec_path[:-5]


def spec_to_bam(spec_path,
                generic_spec_path,
                raw_reference_genome,
                aligner,
                read_groups):
    """Decompresses a SpEC compressed BamFile.

    Registers the new uncompressed file in the database.

    Args:
        spec_path: A string containing the path to the SpEC file on
            Shahlab.
        generic_spec_path: A string containing the path to the SpEC with
            the /archive/shahlab bit not included at the beginning of
            the path.
        raw_reference_genome: A string containing the reference genome,
            which will be interpreted to be either hg18 or hg 19 (or it
            will raise an error).
        aligner: A string containing the BamFile aligner.
        read_groups: A django.db.models.query.QuerySet of read groups
            associated with the bam file.
    Raises:
        A BadReferenceGenomeError if the raw_reference_genome can not be
        interpreted as either hg18 or hg19.
    """
    # Find out what reference genome to use. Currently there are no
    # standardized strings that we can expect, and for reference genomes
    # there are multiple naming standards, so we need to be clever here.
    logging.debug("Parsing reference genome %s", raw_reference_genome)

    found_match = False

    for ref, regex_list in HUMAN_REFERENCE_GENOMES_REGEX_MAP.iteritems():
        for regex in regex_list:
            if re.search(regex, raw_reference_genome, flags=re.I):
                # Found a match
                reference_genome = ref
                found_match = True
                break

        if found_match:
            break
    else:
        # No match was found!
        raise BadReferenceGenomeError(
            raw_reference_genome
            + ' is not a recognized or supported reference genome')

    # Get path of uncompressed BAM
    output_bam_path = get_uncompressed_bam_path(spec_path)
    generic_bam_path = get_uncompressed_bam_path(generic_spec_path)

    # Convert the SpEC to a BAM
    logging.debug("Converting %s", spec_path)

    command = [SHAHLAB_SPEC2BAM_BINARY_PATH,
               '--in',
               spec_path,
               '--ref',
               HUMAN_REFERENCE_GENOMES_MAP[reference_genome],
               '--out',
               output_bam_path,
              ]
    subprocess.check_call(command)

    # Create the new BamFile, starting with the file resource first
    logging.debug("Creating Tantalus instances")

    new_bam_file_resource = FileResource(
        md5=get_file_md5(output_bam_path),
        size=os.path.getsize(output_bam_path),
        created=timezone.now(),
        file_type=FileResource.BAM,
        compression=FileResource.UNCOMPRESSED,
        filename=generic_bam_path,)
    new_bam_file_resource.save()

    # Now the BamFile
    new_bam_file = BamFile(
        reference_genome=raw_reference_genome,
        aligner=aligner,
        bam_file=new_bam_file_resource,)
    new_bam_file.save()

    # Add in the read groups to the bam_file
    new_bam_file.read_groups = read_groups
    new_bam_file.save()

    # Now the file instance
    new_bam_file_instance = FileInstance(
        storage=Storage.objects.get(name=SHAHLAB_TANTALUS_SERVER_NAME),
        file_resource=new_bam_file_resource,)
    new_bam_file_instance.save()


@transaction.atomic
def main():
    """Main script for SpEC to BAM conversion."""
    # Make sure we're on Shahlab
    logging.debug("Checking that we're on Shahlab")

    if socket.gethostname() != SHAHLAB_HOSTNAME:
        print("Must run this script on GSC!", file=sys.stderr)
        sys.exit(1)

    # Parse the JSON args
    logging.debug("Loading JSON arguments")

    json_args = sys.argv[1]
    args_dict = json.loads(json_args)

    # Get the BamFile rows that contains the SpEC files
    logging.debug("Loading BamFiles to process")

    tag_names = args_dict['tags']
    bams = BamFile.objects.filter(tags__name__in=tag_names)

    # Process each BamFile
    for bam in bams:
        logging.debug("Processing BAM file %s", bam.id)

        # Get the SpEC filepath
        file_instance = FileInstance.objects.filter(
            file_resource__id=bam.bam_file.id).filter(
            storage__name=SHAHLAB_TANTALUS_SERVER_NAME).get()
        spec_path = file_instance.get_filepath()

        # Check to make sure there doesn't already exist an uncompressed
        # BAM file
        if os.path.isfile(get_uncompressed_bam_path(spec_path)):
            # The uncompressed BAM file already exists! Move on to the
            # next file.
            logging.warning("An uncompressed BAM file already exists on "
                            "Shahlab! Skipping decompression of SpEC file "
                            "%s.", spec_path)
            continue

        # Convert
        try:
            spec_to_bam(
                spec_path=spec_path,
                generic_spec_path=bam.bam_file.filename,
                raw_reference_genome=bam.reference_genome,
                aligner=bam.aligner,
                read_groups=bam.read_groups.all(),)
        except BadReferenceGenomeError as e:
            logging.exception("Unrecognized reference genome")


if __name__ == '__main__':
    # Run the script
    main()
