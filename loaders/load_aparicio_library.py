import os
import pandas as pd
from tantalus.colossus import *
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tantalus.settings')
django.setup()
from tantalus.models import DNALibrary
cwd = os.getcwd()
os.chdir("..")
os.chdir("loaders/")
# Assign spreadsheet filename to `file`
file = 'aparicio_library.xlsx'
# Load spreadsheet
xl = pd.read_excel(file)
# Load all existing samples in sample
samples=[]
#  Samples in excel used for duplicates
samples_excel=[]

library_dict = {}
library_dict['EXCAP'] = DNALibrary.EXCAP
library_dict['genome-PET'] = DNALibrary.WGS
library_dict['WTSS-PET'] = DNALibrary.RNASEQ
library_dict['miRNA']=DNALibrary.MIRNA
library_dict['Amplicon-SLX-PET'] = DNALibrary.DNA_AMPLICON
library_dict['Exon Capture-400bp'] = DNALibrary.EXCAP
library_dict['ChIP-TS'] = DNALibrary.CHIP
library_dict['Genome-PET'] = DNALibrary.WGS
library_dict['Amp-PET'] = DNALibrary.DNA_AMPLICON
library_dict['Genome-PET/test plate library'] = DNALibrary.WGS
library_dict['Genome-TS (Illumina single end)'] = DNALibrary.WGS
library_dict['miRNA2'] = DNALibrary.MIRNA
library_dict['Genome-PET/ on hold'] = DNALibrary.WGS
library_dict['Genome-PET/ changed to Ex-Capt'] = DNALibrary.EXCAP
library_dict['SOLiD-PE'] = DNALibrary.WGS
library_dict['MRE-Seq'] = DNALibrary.MRE
library_dict['MeDIP-Seq'] = DNALibrary.MEDIP
library_dict['Mi-Seq_targeted sequencing'] = DNALibrary.DNA_AMPLICON
library_dict['bisulfite'] = DNALibrary.BISULFITE
library_dict['ssRNA-Seq-PET'] = DNALibrary.RNASEQ
library_dict['ssRNAseq-unstranded'] = DNALibrary.RNASEQ
library_dict['Genome-HiSeqX'] = DNALibrary.WGS
library_dict['RNAseq'] = DNALibrary.RNASEQ
library_dict['WGS']=DNALibrary.WGS
library_dict['HiSeq 2500']=DNALibrary.CHIP

# samples_duplicate: contains the new sample_ids that has been created.It is used to check for duplicates.
samples_duplicate = []
def recheck_sample_id(sample_id,sample):
    last_char = sample_id.split("_")[-1]
    new_last_char = int(last_char) + 1
    sample_id = str(sample) + "_" + str(new_last_char)
    samples_duplicate.append(sample_id)
    return sample_id

def get_new_sample_id(sample):
    if [x for x in samples_duplicate if x.startswith(sample)]:
        matches = [x for x in (samples_duplicate) if (sample) in x]
        s = (matches[-1])
        last_char =  s.split("_")[-1]
        new_last_char = int(last_char) + 1
        sample_id = str(sample) + "_"+str(new_last_char)
        # Append the new sample id created
        samples_duplicate.append(sample_id)
        # Make sure the new sample_id is unique
        while sample_id in matches:
            sample_id =recheck_sample_id(sample_id,sample)
        return sample_id
    else:
        sample_id=sample + "_" +str(1)
        samples_duplicate.append(sample_id)
        return sample_id


def get_patient_id(sample):
    # Validate id
    letter=''
    if sample.startswith('DAH'):
            prefix = sample[0:3]
            try:
                num = str(sample[3:4])
                assert num.isdigit()
            except ValueError or AssertionError as e:
                print e
                raise
    elif sample.startswith('SA') or sample.startswith('DA'):
            prefix= sample[0:2]
            try:
                num=str(sample[2:3])
                assert num.isdigit()
            except AssertionError as e:
                print e
                raise
    else:
        return ' '
    # Slice to get the patient id
    a = sample.split(prefix)
    for x in a[1]:
        if x.isnumeric():
            letter += x
        else:
            break
    patient_id= prefix+letter
    return patient_id


def get_sample_id(sample):
    # Create new sample id if its a duplicate
    if sample in samples_excel:
        sample_id = get_new_sample_id(sample)
    else:
        sample_id = sample
        samples_excel.append(sample_id)
    return sample_id

def new_library(library_id):
    if library_id == 'failed'  :
        return
    elif library_id == ('no library'):
        return
    else:
        return library_id

def create_new_excel():
    new_df_list=[]
    for index,row in xl.iterrows():
        library_id = row['Library (Lims ID)']
        date_submission = row['Date Sample Submission ']
        library_type = row['Library Type']
        submitted_by = row['Submitted by']
        project_name = row['Project name']
        collab_sample = row['EXTERNAL Sample ID ']
        tissue = row['Tissue/Cell line']
        sow = row['SOW']
        note = row['Note']
        lanes_sequenced = row['Lanes Sequenced']
        original_goal= row['Original Goal']
        updated_goal = row['Updated Goal']
        data_path = row['Data Path (/projects/analysis)']
        payment = row['Payment']
        # Check for null sample id and get the sample id/patient id
        if not pd.isnull(row['Sample ID']):
            sample_id= get_sample_id(row['Sample ID'])
            patient_id = get_patient_id(row['Sample ID'])
        else:
            sample_id = 'nan'
            patient_id = 'nan'
        if not pd.isnull(library_id):
            new_lib = new_library(library_id)
            try:
                new_lib_type = library_dict[library_type]
            except KeyError as e:
                print e
                new_lib_type = " "
        else:
            new_lib ='nan'
            new_lib_type='nan'

        new_df_list.append({
            'Sample ID':sample_id,
            'Patient ID':patient_id,
            'External Sample ID':collab_sample,
            'note':note,
            'Tissue':tissue,
            'Spreadsheet Sample ID':row['Sample ID'],
            'Library ID':new_lib,
            'Library type':new_lib_type,
            'Date sample submission':date_submission,
            'Project name':project_name,
            'Sow':sow,
            'Submitted by':submitted_by,
            'Payment':payment,
            'Data Path':data_path,
            'Lanes sequenced':lanes_sequenced,
            'Updated goal':updated_goal,
            'Original goal':original_goal
        })
    df1 = pd.DataFrame(new_df_list,columns=['Sample ID','Patient ID','External Sample ID','note','Tissue','Spreadsheet Sample ID','Library ID','Library type','Date sample submission','Project name','Sow','Submitted by','Payment','Data path','Lanes sequenced','Updated goal','Original goal'])
    # Create a Pandas Excel writer using XlsxWriter as the engine.
    writer = pd.ExcelWriter('final_excel.xlsx', engine='xlsxwriter')
    # Convert the dataframe to an XlsxWriter Excel object.
    df1.to_excel(writer, sheet_name='Sheet1')
    # Close the Pandas Excel writer and output the Excel file.
    writer.save()

def check_for_duplicates():
    file = 'final_excel.xlsx'
    # Load spreadsheet
    xl = pd.read_excel(file,converters={'Data Path':str,'note':str,'Payment':str})
    # Check for sample ID duplicate
    duplicated_samples  = xl[xl.duplicated(subset='Sample ID')]['Sample ID']
    print "Duplicated samples"
    print duplicated_samples

    duplicated_libraries = xl[xl.duplicated(subset='Library ID')]['Library ID']
    print "Duplicated library"
    for l in duplicated_libraries:
        print l

create_new_excel()
check_for_duplicates()