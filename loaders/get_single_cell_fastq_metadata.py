import pandas as pd
import subprocess
import os
import time
import sys
from multiprocessing import Pool


def get_md5(filename):
    try:
        return subprocess.check_output(['md5sum', filename]).split()[0]
    except Exception as e:
        print e
        return None


def get_size(filename):
    try:
        return os.path.getsize(filename)
    except Exception as e:
        print e
        return None


def get_create(filename):
    try:
        return pd.Timestamp(time.ctime(os.path.getmtime(filename)))
    except Exception as e:
        print e
        return None


data = pd.read_csv('loaders/single_cell_hiseq_fastq.tsv', sep='\t')

p = Pool(32)

data['md51'] = p.map(get_md5, data['read1'].values)
data['md52'] = p.map(get_md5, data['read2'].values)
data['size1'] = p.map(get_size, data['read1'].values)
data['size2'] = p.map(get_size, data['read2'].values)
data['create1'] = p.map(get_create, data['read1'].values)
data['create2'] = p.map(get_create, data['read2'].values)

with pd.HDFStore('loaders/single_cell_hiseq_fastq_metadata.h5', 'w') as store:
    store['metadata'] = data

