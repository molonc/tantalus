import os
import sys
import string
import pandas as pd
import django
import paramiko


sys.path.append('./')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tantalus.settings')
django.setup()
DIRECTORY_TO_STRIP = "/share/lustre/archive/single_cell_indexing/HiSeq/"

import tantalus.models

def reverse_complement(sequence):
    return sequence[::-1].translate(string.maketrans('ACTGactg','TGACtgac'))


def get_sam_header_information(file_to_bam):
    #TODO: ask andrew for help
    libraries = pd.HDFStore('loaders/single_cell_hiseq_fastq_metadata.h5', 'r')['/metadata']['id']
    return libraries


def get_or_create_scraped_samples():
    df = pd.DataFrame.from_csv('scrapers/bulk_bam.txt', sep='\t', index_col=None)
    samples = set(df['sample_id'])
    for s in samples:
        tantalus.models.Sample.objects.get_or_create(
            sample_id=s
        )


def get_or_create_scraped_dna_library():
    df = pd.DataFrame.from_csv('scrapers/bulk_bam.txt', sep='\t', index_col=None)
    libs = set(df['library_id'])
    for lib in libs:
        tantalus.models.DNALibrary.objects.get_or_create(
            library_id=lib,
            #TODO: ask andrew what to fill in for the other fields of DNA Library..
        )





if __name__ == '__main__':
    # make calls to the function here when you run the script to load in data
    print "hi tim"