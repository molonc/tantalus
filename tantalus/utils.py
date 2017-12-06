from __future__ import absolute_import
from tantalus.models import FileTransfer
import tantalus.tasks
from celery import chain
import pandas as pd


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


