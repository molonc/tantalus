import os
import pandas as pd
from tantalus.colossus import *
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tantalus.settings')
cwd = os.getcwd()
os.chdir("..")
os.chdir("loaders/")
# Assign spreadsheet filename to `file`

def is_unique_library(df):
    if len(df['Library Type'].unique()) > 1:
        return True
    return False

def get_problematic_library():
    file1 = 'aparicio_library.xlsx'
    xl = pd.read_excel(file1)
    is_problematic = xl.groupby('Library (Lims ID)').apply(is_unique_library).rename('is_problematic').reset_index()
    writer_final = pd.ExcelWriter('dup_library.xlsx', engine='xlsxwriter')
    df = xl.merge(is_problematic)
    df = df[df['is_problematic']]
    df = df.to_excel(writer_final, sheet_name='Sheet1',
                     columns=['Library (Lims ID)', 'Library Type'])

def is_unique_sample(df):
    if len(df['EXTERNAL Sample ID '].unique()) > 1:
        return True
    if len(df['Tissue/Cell line'].unique()) > 1:
        return True
    if len(df['Note'].unique()) > 1:
        return True
    if len(df['Project name'].unique()) > 1:
        return True
    return False

def get_problematic_samples():
    file = 'aparicio_library.xlsx'
    # Load spreadsheet.tra
    xl = pd.read_excel(file)
    # Get all duplicated samples as only_duplicated_samples.xlsx
    writer = pd.ExcelWriter('only_duplicated_samples.xlsx', engine='xlsxwriter')
    duplicate_samples = xl[xl.duplicated(subset='Sample ID', keep=False)]
    duplicate_samples = duplicate_samples.to_excel(writer, sheet_name='Sheet1',
                                                   columns=['Sample ID', 'EXTERNAL Sample ID ', 'Project name',
                                                            'Tissue/Cell line', 'Note'])
    writer.save()
    file1 = 'only_duplicated_samples.xlsx'
    xl = pd.read_excel(file1)
    is_problematic = xl.groupby('Sample ID').apply(is_unique_sample).rename('is_problematic').reset_index()
    writer_final = pd.ExcelWriter('problematic_samples.xlsx', engine='xlsxwriter')
    df = xl.merge(is_problematic)
    df = df[df['is_problematic']]
    dl = df.to_excel(writer_final, sheet_name='Sheet1', columns=['Sample ID', 'Tissue/Cell line', 'EXTERNAL Sample ID ','Note','Project name'])

get_problematic_samples()