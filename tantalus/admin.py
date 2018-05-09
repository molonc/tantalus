from django.contrib import admin

from tantalus.models import *
from tantalus.generictask_models import GenericTaskType, GenericTaskInstance


admin.site.register(AzureBlobCredentials)
admin.site.register(Sample)
admin.site.register(DNALibrary)
admin.site.register(SequenceLane)
admin.site.register(ReadGroup)
admin.site.register(FileResource)
admin.site.register(SingleEndFastqFile)
admin.site.register(PairedEndFastqFiles)
admin.site.register(BamFile)
admin.site.register(Storage)
admin.site.register(ServerStorage)
admin.site.register(AzureBlobStorage)
admin.site.register(FileInstance)
admin.site.register(FileTransfer)
admin.site.register(GenericTaskType)
admin.site.register(GenericTaskInstance)
