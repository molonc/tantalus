import os
import math
import pandas as pd
import django
import ast
import sys
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
sys.path.append('./')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tantalus.settings')
django.setup()
from tantalus.models import DNALibrary,Sample,Submission,Sow,Project,Patient
os.chdir("loaders/")
UNIQUE_CONSTRAINT_SAMPLES = []
# Assign spreadsheet filename to `file`
def get_projects(projects):
    result=[]
    list_projects = ast.literal_eval(projects)
    for x in list_projects:
        if not x =="":
            result.append(x)
    return result


def load_projects():
    # LOAD INTO Project
    xl1 = pd.read_csv('Final_app.csv')
    for index, row in xl1.iterrows():
        result = get_projects(row['Project name'])
        for proj in result:
            obj, created = Project.objects.get_or_create(name=proj)

def load_library(library_id,library_type):
    # LOAD INTO LIBRARY
    obj, created = DNALibrary.objects.update_or_create(
        library_id=library_id,
        defaults={'library_type': library_type},)

def load_sow(sow):
    # LOAD INTO Sow
    obj,created = Sow.objects.get_or_create(name=sow)

def load_patient():
    file = 'Final_app.csv'
    # Load spreadsheet
    xl1 = pd.read_csv(file)
    for index,row in xl1.iterrows():
        patient = get_patient_id(row['Sample ID'])
        p, c = Patient.objects.get_or_create(patient_id=patient)


def load_sample(sample_id,patient_id,external_sample,tissue,note,projects):
    patient = get_patient_id(patient_id)
    p= Patient.objects.get(patient_id=patient)
    if pd.isnull(external_sample):
        collab_sample = ' '
    else:
        collab_sample =external_sample
    if pd.isnull(note):
        extra = ' '
    else:
        extra =note
    if pd.isnull(tissue):
        tissue_final = ' '
    else:
        tissue_final = tissue
    try:
        obj, created = Sample.objects.update_or_create(
            sample_id=sample_id,
            defaults={
            'collab_sample_id':collab_sample,
            'tissue':tissue_final,
            'note':extra,
            'patient_id':p,
            }
        )
        result = get_projects(projects)
        # print result
        if result:
            for project in result:
                if project:
                    project = Project.objects.get(name=project)
                    obj.projects.add(project)
                    obj.save()
    except IntegrityError as e:
        print e


def load_submission(sample_id,library_type,date_submission,sow,submitted_by,lanes_sequenced,updated_goal,payment,data_path):
    if not sample_id  == 'nan':
        sample= Sample.objects.get(sample_id=sample_id)
        if sample:
            try:
                sow_name= Sow.objects.get(name=sow)
            except ObjectDoesNotExist:
                sow_name=None
            obj,created = Submission.objects.get_or_create(
                    sample=sample,
                    sow=sow_name,
                    submission_date=date_submission,
                    submitted_by=submitted_by,
                    lanes_sequenced=lanes_sequenced,
                    updated_goal=updated_goal,
                    payment=payment,
                    data_path = data_path,
                    library_type = library_type
                )


def validate_lanes_sequenced(lanes_sequenced):
    try:
        if math.isnan(lanes_sequenced):
            lanes_sequenced = None
            return lanes_sequenced
        else:
            return lanes_sequenced
    except ValueError:
        lanes_sequenced = None
        return lanes_sequenced
    except TypeError:
        lanes_sequenced = None
        return lanes_sequenced


def validate_update_goal(updated_goal):
    try:
        if math.isnan(updated_goal):
            updated_goal = None
            return updated_goal
        else:
            return updated_goal
    except ValueError:
        updated_goal = None
        return updated_goal
    except TypeError:
        updated_goal = None
        return updated_goal


def get_patient_id(sample):
    # Validate id
    letter=''
    if sample.startswith('DAH'):
            prefix = sample[0:3]
            try:
                num = sample[3:4]
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
        if x.isdigit():
            letter += x
        else:
            break
    patient_id= prefix+letter
    return patient_id


def load_libraries():
    file = 'final_excel.xlsx'
    # Load spreadsheet
    xl = pd.read_excel(file, converters={'Data Path': str, 'note': str, 'Payment': str})
    for index, row in xl.iterrows():
        load_library(row['Library ID'],row['Library type'])


def load_submissions():
    file = 'final_excel.xlsx'
    # Load spreadsheet
    xl = pd.read_excel(file, converters={'Data Path': str, 'note': str, 'Payment': str})
    for index, row in xl.iterrows():
            try:
                final_updated_goal = validate_update_goal(row['Updated goal'])
                final_lanes_sequenced = validate_lanes_sequenced(row['Lanes sequenced'])
                load_submission(row['Spreadsheet Sample ID'],row['Library type'],row['Date sample submission'],row['Sow'],row['Submitted by'],final_lanes_sequenced,final_updated_goal,row['Payment'],row['Data path'])
            except IntegrityError as e:
                print e
                UNIQUE_CONSTRAINT_SAMPLES.append({'Sample ID':row['Spreadsheet Sample ID'],'Library type':row['Library type'],'date submission':row['Date sample submission']})
                continue
            except ObjectDoesNotExist as e:
                continue


def load_sows():
    file = 'final_excel.xlsx'
    # Load spreadsheet
    xl = pd.read_excel(file, converters={'Data Path': str, 'note': str, 'Payment': str})
    for index, row in xl.iterrows():
        obj,created = Sow.objects.get_or_create(name=row['Sow'])


def load_all_samples():
    xl1 = pd.read_csv('Final_app.csv')
    for index,row in xl1.iterrows():
                load_sample(sample_id=row['Sample ID'],patient_id=row['Sample ID'],external_sample=row['EXTERNAL Sample ID '],note=row['Extra'],tissue=row['Tissue/Cell line'],projects=row['Project name'])


load_patient()
load_projects()
load_all_samples()
load_libraries()
load_sows()
load_submissions()
