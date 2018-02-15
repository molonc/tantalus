import os
import pandas as pd
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tantalus.settings')
cwd = os.getcwd()
os.chdir("..")
os.chdir("loaders/")
# Assign spreadsheet filename to `file`
original_samples = 'aparicio_library.xlsx'
problem_samples = 'problem_sample.csv'
# Load spreadsheet
xl_app = pd.read_excel(original_samples)
xl2 = pd.read_csv(problem_samples)
xl_app = xl_app.replace(pd.np.nan, '', regex=True)
unique_sample_id = xl_app['Sample ID'].unique().tolist()
dup = xl2['Sample ID'].tolist()
# Compare the original excel with the problematics samples and get the ones that are not present in the problem_sample.csv
only_unique = list(set(unique_sample_id) - set(dup))
frames=[]
for i in only_unique:
    if i:
        df1 = (xl_app.loc[xl_app['Sample ID']==i,['Sample ID','EXTERNAL Sample ID ','Tissue/Cell line','Note','Project name']])
        df1['Extra']=df1['Note']
        df1['Project name'] = [x.lower() for x in df1['Project name']]
        df1['Project name'] = [[x] for x in df1['Project name']]
        df1['Project name'] = df1['Project name'].astype(str)
        df1 =df1[['Sample ID','EXTERNAL Sample ID ','Tissue/Cell line','Note','Extra','Project name']]
        frames.append(df1)
xl2  = xl2.append([x for x in frames])
xl2 = xl2[['Sample ID','EXTERNAL Sample ID ','Tissue/Cell line','Extra','Note','Project name']]
xl2 = xl2.to_csv('Final_app.csv',encoding="utf-8")