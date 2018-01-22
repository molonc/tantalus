import django
import os
import pandas as pd
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tantalus.settings')
django.setup()
from tantalus.models import FileInstance

def fix_filename_override():
    df = pd.DataFrame.from_csv("scrapers/bulk_bam_metadata.csv")

    with open('loaders/added_files', 'r') as f:
        added_files = f.readlines()

    files = []
    for line in added_files:
        line = line.strip('\n')
        files.append(line)


    for index, line in df.iterrows():
        if line.path not in files:
            continue

        try:
            Bam = FileInstance.objects.filter(filename_override=line.file)[0]
            Bam.filepath = line.path
            Bam.filename_override = line.path
            Bam.save()
        except Exception as e:
            print (line.path + " failed with " + str(e.message))

if __name__ == '__main__':
    fix_filename_override()
