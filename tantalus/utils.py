from __future__ import absolute_import
from tantalus.models import FileTransfer
import tantalus.tasks
from celery import chain
import pandas as pd
import csv


def read_excel_sheets(filename):
    """ 
    Load and read an excel file, extracting specific columns.
    """
    
    required_columns = ['sample_id']

    try:
        data = pd.read_excel(filename, sheetname=None)
    except IOError:
        raise ValueError('Unable to find file', filename)
    
    # convert all column names in the loaded file to lowercase
    for sheetname in data:
            data[sheetname].columns = [c.lower() for c in data[sheetname].columns]

    for sheetname in data:
        if set(required_columns).issubset(data[sheetname].columns):
            yield data[sheetname]


def start_md5_checks(file_instances):
    """
    Start md5 check jobs on file instances.
    """

    for file_instance in file_instances:
        md5_check = tantalus.models.MD5Check(
            file_instance=file_instance
        )
        md5_check.save()

        tantalus.tasks.check_md5_task.apply_async(args=(md5_check.id,), queue=file_instance.storage.get_md5_queue_name())


def parse_summary_file(summary_file):
    """
    Extracts information from gsc library summary files
    library -> LIBRARY -> library_id
    external_identifier -> EXTERNAL_ID -> sample_id 
    """

    library_id = None
    sample_id = None

    with open(summary_file, 'r') as file:
        reader = csv.reader(file, delimiter='\t')
        
        # read line 27
        for i in range(27): row = next(reader)
        library_id = row[2]
        sample_id = row[13]
