from django.contrib import admin

from tantalus.models import *
from tantalus.generictask_models import GenericTaskType, GenericTaskInstance


admin.site.register(Tag)
admin.site.register(Project)
admin.site.register(Patient)
admin.site.register(Sample)
admin.site.register(DNALibrary)
admin.site.register(SequencingLane)
admin.site.register(FileResource)
admin.site.register(SequenceDataset)
admin.site.register(Storage)
admin.site.register(ServerStorage)
admin.site.register(AzureBlobCredentials)
admin.site.register(AzureBlobStorage)
admin.site.register(FileInstance)
admin.site.register(BRCFastqImport)
admin.site.register(FileTransfer)
admin.site.register(ReservedFileInstance)
admin.site.register(MD5Check)
admin.site.register(GscWgsBamQuery)
admin.site.register(GscDlpPairedFastqQuery)
admin.site.register(ImportDlpBam)
admin.site.register(Sow)
admin.site.register(Submission)
