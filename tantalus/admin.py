from django.contrib import admin

from tantalus.models import *

class FileInstanceAdmin(admin.ModelAdmin):
    raw_id_fields = ('file_resource', )

class SequenceDatasetAdmin(admin.ModelAdmin):
    raw_id_fields = ('tags', 'sample', 'library', 'file_resources', 'sequence_lanes', 'analysis', )

class ResultsDatasetAdmin(admin.ModelAdmin):
    raw_id_fields = ('tags', 'analysis', 'samples', 'libraries', 'file_resources', )

class SequencingLanesAdmin(admin.ModelAdmin):
    raw_id_fields = ('dna_library',)

class CurationAdmin(admin.ModelAdmin):
    class Meta:
        model = Curation
    filter_horizontal = ('sequencedatasets',)

admin.site.register(Tag)
admin.site.register(Project)
admin.site.register(Patient)
admin.site.register(Sample)
admin.site.register(LibraryType)
admin.site.register(DNALibrary)
admin.site.register(SequencingLane, SequencingLanesAdmin)
admin.site.register(FileResource)
admin.site.register(ReferenceGenome)
admin.site.register(AlignmentTool)
admin.site.register(SequenceDataset, SequenceDatasetAdmin)
admin.site.register(Storage)
admin.site.register(ServerStorage)
admin.site.register(AzureBlobStorage)
admin.site.register(AwsS3Storage)
admin.site.register(FileInstance, FileInstanceAdmin)
admin.site.register(Sow)
admin.site.register(Submission)
admin.site.register(AnalysisType)
admin.site.register(ResultsDataset, ResultsDatasetAdmin)
admin.site.register(CurationHistory)
admin.site.register(Curation, CurationAdmin)
