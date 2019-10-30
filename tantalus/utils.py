from __future__ import absolute_import
import pandas as pd
import csv
import tantalus.models

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


def create_curation_history(curation, user_name, operation, operation_description, version):
    '''
    Create a curation history object with the values provided.
    '''
    history_object = tantalus.models.CurationHistory(
            curation=curation,
            user_name=user_name,
            operation=operation,
            operation_description=operation_description,
            version=version
            )
    return history_object

def create_curation_modification_detail(log_message, operation, curation_instance):
    '''
    Create a dict of curation modification history that is used to send to the frontend.
    '''
    modification_detail = {
        "operation": operation,
        "user": curation_instance.user,
        "operation_log": log_message,
        "updated": curation_instance.updated,
        "version": curation_instance.version
        }
    return modification_detail
