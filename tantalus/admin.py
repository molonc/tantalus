from django.contrib import admin

from tantalus.models import *


admin.site.register(Tag)
admin.site.register(Project)
admin.site.register(Patient)
admin.site.register(Sample)
admin.site.register(DNALibrary)
admin.site.register(SequencingLane)
admin.site.register(FileType)
admin.site.register(FileResource)
admin.site.register(SequenceDataset)
admin.site.register(Storage)
admin.site.register(ServerStorage)
admin.site.register(AzureBlobCredentials)
admin.site.register(AzureBlobStorage)
admin.site.register(FileInstance)
admin.site.register(Sow)
admin.site.register(Submission)
