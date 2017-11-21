from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAdminUser
import django_filters
import tantalus.models
import tantalus.api.serializers


class SampleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = tantalus.models.Sample.objects.all()
    serializer_class = tantalus.api.serializers.SampleSerializer
    filter_fields = ('sample_id',)


class FileResourceFilterSet(django_filters.FilterSet):
    library_id = django_filters.CharFilter(name='dataset__dna_sequences__dna_library__library_id')
    class Meta:
        model = tantalus.models.FileResource
        fields = ['library_id']


class FileResourceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = tantalus.models.FileResource.objects.all()
    serializer_class = tantalus.api.serializers.FileResourceSerializer
    filter_class = FileResourceFilterSet


class DNALibraryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = tantalus.models.DNALibrary.objects.all()
    serializer_class = tantalus.api.serializers.DNALibrarySerializer
    filter_fields = ('library_id',)


class DNASequencesViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = tantalus.models.DNASequences.objects.all()
    serializer_class = tantalus.api.serializers.DNASequencesSerializer
    filter_fields = ('dna_library__library_id', 'dna_library', 'index_sequence')


class SequenceLaneViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = tantalus.models.SequenceLane.objects.all()
    serializer_class = tantalus.api.serializers.SequenceLaneSerializer
    filter_fields = ('flowcell_id', 'lane_number', 'dna_library__library_id')


class AbstractDataSetViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = tantalus.models.AbstractDataSet.objects.all()
    serializer_class = tantalus.api.serializers.AbstractDataSetSerializer
    filter_fields = (
                     # filters for SequenceLanes
                     'lanes',
                     'lanes__flowcell_id', 'lanes__lane_number',
                     # filters for DNASequences
                     'dna_sequences',
                     'dna_sequences__dna_library__library_id', 'dna_sequences__dna_library', 'dna_sequences__index_sequence'
                     )


class SingleEndFastqFileViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = tantalus.models.SingleEndFastqFile.objects.all()
    serializer_class = tantalus.api.serializers.SingleEndFastqFileSerializer


class PairedEndFastqFilesFilterSet(django_filters.FilterSet):
    library_id = django_filters.CharFilter(name='dna_sequences__dna_library__library_id')
    index_sequence = django_filters.CharFilter(name='dna_sequences__index_sequence')
    class Meta:
        model = tantalus.models.PairedEndFastqFiles
        fields = ['library_id', 'index_sequence']


class PairedEndFastqFilesViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = tantalus.models.PairedEndFastqFiles.objects.all()
    filter_class = PairedEndFastqFilesFilterSet
    serializer_class = tantalus.api.serializers.PairedEndFastqFilesSerializer


class BamFileFilterSet(django_filters.FilterSet):
    library_id = django_filters.CharFilter(name='dna_sequences__dna_library__library_id')
    sample_id = django_filters.CharFilter(name='dna_sequences__sample__sample_id')
    class Meta:
        model = tantalus.models.BamFile
        fields = ['library_id', 'sample_id']


class BamFileViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = tantalus.models.BamFile.objects.all()
    serializer_class = tantalus.api.serializers.BamFileSerializer
    filter_class = BamFileFilterSet


class StorageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = tantalus.models.Storage.objects.all()
    serializer_class = tantalus.api.serializers.StorageSerializer
    filter_fields = ('name',)


class ServerStorageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = tantalus.models.ServerStorage.objects.all()
    serializer_class = tantalus.api.serializers.ServerStorageSerializer
    filter_fields = ('name',)


class AzureBlobStorageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = tantalus.models.AzureBlobStorage.objects.all()
    serializer_class = tantalus.api.serializers.AzureBlobStorageSerializer


class FileInstanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = tantalus.models.FileInstance.objects.all()
    serializer_class = tantalus.api.serializers.FileInstanceSerializer
    filter_fields = ('file_resource__md5', 'file_resource',
                     'storage__name',)


class DeploymentViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.Deployment.objects.all()
    serializer_class = tantalus.api.serializers.DeploymentSerializer
    filter_fields = ('name',)


class FileTransferViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.FileTransfer.objects.all()
    serializer_class = tantalus.api.serializers.FileTransferSerializer


class MD5CheckViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.MD5Check.objects.all()
    serializer_class = tantalus.api.serializers.MD5CheckSerializer


class BRCImportFastqsViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.BRCFastqImport.objects.all()
    serializer_class = tantalus.api.serializers.ImportBRCFastqsSerializer


class QueryGscWgsBamsViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.GscWgsBamQuery.objects.all()
    serializer_class = tantalus.api.serializers.QueryGscWgsBamsSerializer


class QueryGscDlpPairedFastqsViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.GscDlpPairedFastqQuery.objects.all()
    serializer_class = tantalus.api.serializers.QueryGscDlpPairedFastqsSerializer
    filter_fields = ('dlp_library_id',)

