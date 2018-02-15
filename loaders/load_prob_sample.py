import os
import pandas as pd
from tantalus.colossus import *
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tantalus.settings')
cwd = os.getcwd()
os.chdir("..")
os.chdir("loaders/")
# Assign spreadsheet filename to `file`
file = 'problematic_samples.xlsx'
# Load spreadsheet.tra
xl = pd.read_excel(file)
xl = xl.replace(pd.np.nan, '', regex=True)

# Get all unique sample id
unique_sample_id = xl['Sample ID'].unique()
es = [(xl.loc[xl['Sample ID']==i,['EXTERNAL Sample ID ']]).values.tolist()[0] for i in unique_sample_id]
ts = [(xl.loc[xl['Sample ID']==i,['Tissue/Cell line']]).values.tolist()[0] for i in unique_sample_id]
note = [(xl.loc[xl['Sample ID']==i,['Note']]).values.tolist()[0] for i in unique_sample_id]
project = [(xl.loc[xl['Sample ID']==i,['Project name']]).values.tolist()[0] for i in unique_sample_id]
# Flattening the list
df_unique = pd.DataFrame({'Sample ID':[x for x in unique_sample_id]})
external_sampleunique_flattened = [y for x in es for y in x]
tissue_listunique_flattened = [y for x in ts for y in x]
note_listunique_flattened = [y for x in note for y in x]
project_listunique_flattened = [y for x in project for y in x]

df_unique['EXTERNAL Sample ID ']= pd.Series(external_sampleunique_flattened)
df_unique['Tissue/Cell line'] = pd.Series(tissue_listunique_flattened)
df_unique['Note'] = pd.Series(note_listunique_flattened)
df_unique['Project name'] = pd.Series(project_listunique_flattened)

frames_extra =[]
projects = []
#  Get all the duplicated related fields
for i in unique_sample_id:
    df1 = (xl.loc[xl['Sample ID']==i,['EXTERNAL Sample ID ','Tissue/Cell line','Note']])
    df1['Note']=[x.encode("utf-8") for x in df1['Note']]
    df1['EXTERNAL Sample ID ']=[x.encode("utf-8") for x in df1['EXTERNAL Sample ID ']]
    df1['Tissue/Cell line']=[x.encode("utf-8") for x in df1['Tissue/Cell line']]
    df2 = (xl.loc[xl['Sample ID']==i,['Project name']])
    df2['Project name']=[x.encode("utf-8") for x in df2['Project name']]
    list_proj = df2['Project name'].values.tolist()
    list_proj = [x.strip() for x in list_proj]
    list_proj = [x.lower() for x in list_proj]
    list_proj = list(set(list_proj))
    projects.append(list_proj)
    extra = repr(df1.to_dict(orient='records'))
    frames_extra.append(extra)
df_unique['Extra']= pd.Series(frames_extra)
df_unique['Project name']=pd.Series(projects).astype(str)
df_unique['Extra']= df_unique['Extra'].astype(str).values
df_unique = df_unique.to_csv('problem_sample.csv',encoding='utf-8')


