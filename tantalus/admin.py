from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from tantalus.models import *

class FileInstanceAdmin(SimpleHistoryAdmin, admin.ModelAdmin):
    raw_id_fields = ('file_resource', )

class SequenceDatasetAdmin(SimpleHistoryAdmin, admin.ModelAdmin):
    raw_id_fields = ('tags', 'sample', 'library', 'file_resources', 'sequence_lanes', 'analysis', )

class ResultsDatasetAdmin(SimpleHistoryAdmin, admin.ModelAdmin):
    raw_id_fields = ('tags', 'analysis', 'samples', 'libraries', 'file_resources', )

class SequencingLanesAdmin(SimpleHistoryAdmin, admin.ModelAdmin):
    raw_id_fields = ('dna_library',)

class AnalysisAdmin(SimpleHistoryAdmin, admin.ModelAdmin):
    raw_id_fields = ('logs', )

class CurationAdmin(SimpleHistoryAdmin, admin.ModelAdmin):
    class Meta:
        model = Curation
    def has_change_permission(self, request, obj=None):
        return False

admin.site.register(Tag, SimpleHistoryAdmin)
admin.site.register(Project, SimpleHistoryAdmin)
admin.site.register(Patient, SimpleHistoryAdmin)
admin.site.register(Sample, SimpleHistoryAdmin)
admin.site.register(LibraryType, SimpleHistoryAdmin)
admin.site.register(DNALibrary, SimpleHistoryAdmin)
admin.site.register(SequencingLane, SequencingLanesAdmin)
admin.site.register(FileResource, SimpleHistoryAdmin)
admin.site.register(ReferenceGenome, SimpleHistoryAdmin)
admin.site.register(AlignmentTool, SimpleHistoryAdmin)
admin.site.register(SequenceDataset, SequenceDatasetAdmin)
admin.site.register(Storage, SimpleHistoryAdmin)
admin.site.register(ServerStorage, SimpleHistoryAdmin)
admin.site.register(AzureBlobStorage, SimpleHistoryAdmin)
admin.site.register(AwsS3Storage, SimpleHistoryAdmin)
admin.site.register(FileInstance, FileInstanceAdmin)
admin.site.register(Sow, SimpleHistoryAdmin)
admin.site.register(Submission, SimpleHistoryAdmin)
admin.site.register(Analysis, AnalysisAdmin)
admin.site.register(AnalysisType, SimpleHistoryAdmin)
admin.site.register(ResultsDataset, ResultsDatasetAdmin)
admin.site.register(Curation, CurationAdmin)

