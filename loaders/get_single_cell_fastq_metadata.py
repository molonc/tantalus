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

# print 'getting stats for {} fastqs'.format(len(data.index))
# print 'printing `.` for every file pair'
# 
# for idx in data.index:
#     sys.stdout.write('.')
#     sys.stdout.flush()
#     for read_end in ('1', '2'):
#         fastq_filename = data.loc[idx, 'read' + read_end]
#         try:
#             md5 = subprocess.check_output(['md5sum', fastq_filename]).split()[0]
#         except Exception as e:
#             print e
#             md5 = None
#         data.loc[idx, 'md5' + read_end] = md5
#         try:
#             size = os.path.getsize(fastq_filename)
#         except Exception as e:
#             print e
#             size = None
#         data.loc[idx, 'size' + read_end] = size
#         try:
#             create = pd.Timestamp(time.ctime(os.path.getmtime(fastq_filename)))
#         except Exception as e:
#             print e
#             create = None
#         data.loc[idx, 'create' + read_end] = create

print data

