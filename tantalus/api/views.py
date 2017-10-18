from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
import django_filters
import tantalus.models
import tantalus.api.serializers


class SampleViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.Sample.objects.all()
    serializer_class = tantalus.api.serializers.SampleSerializer
    filter_fields = ('sample_id',)


class FileResourceFilterSet(django_filters.FilterSet):
    library_id = django_filters.CharFilter(name='dataset__dna_sequences__dna_library__library_id')
    class Meta:
        model = tantalus.models.FileResource
        fields = ['library_id']


class FileResourceViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.FileResource.objects.all()
    serializer_class = tantalus.api.serializers.FileResourceSerializer
    filter_class = FileResourceFilterSet


class DNALibraryViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.DNALibrary.objects.all()
    serializer_class = tantalus.api.serializers.DNALibrarySerializer
    filter_fields = ('library_id',)


class DNASequencesViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.DNASequences.objects.all()
    serializer_class = tantalus.api.serializers.DNASequencesSerializer
    filter_fields = ('dna_library__library_id', 'dna_library', 'index_sequence')


class SequenceLaneViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.SequenceLane.objects.all()
    serializer_class = tantalus.api.serializers.SequenceLaneSerializer
    filter_fields = ('flowcell_id', 'lane_number', 'dna_library__library_id')


class AbstractDataSetViewSet(viewsets.ModelViewSet):
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


class SingleEndFastqFileViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.SingleEndFastqFile.objects.all()
    serializer_class = tantalus.api.serializers.SingleEndFastqFileSerializer


class PairedEndFastqFilesFilterSet(django_filters.FilterSet):
    library_id = django_filters.CharFilter(name='dna_sequences__dna_library__library_id')
    class Meta:
        model = tantalus.models.PairedEndFastqFiles
        fields = ['library_id']


class PairedEndFastqFilesViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.PairedEndFastqFiles.objects.all()
    filter_class = PairedEndFastqFilesFilterSet
    def get_serializer_class(self):
        if self.request.method in ('GET',):
            return tantalus.api.serializers.PairedEndFastqFilesReadSerializer
        return tantalus.api.serializers.PairedEndFastqFilesSerializer


class BamFileViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.BamFile.objects.all()
    serializer_class = tantalus.api.serializers.BamFileSerializer


class StorageViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.Storage.objects.all()
    serializer_class = tantalus.api.serializers.StorageSerializer
    permission_classes = (IsAdminUser,)


class ServerStorageViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.ServerStorage.objects.all()
    serializer_class = tantalus.api.serializers.ServerStorageSerializer
    permission_classes = (IsAdminUser,)


class AzureBlobStorageViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.AzureBlobStorage.objects.all()
    serializer_class = tantalus.api.serializers.AzureBlobStorageSerializer
    permission_classes = (IsAdminUser,)


class FileInstanceViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.FileInstance.objects.all()
    serializer_class = tantalus.api.serializers.FileInstanceSerializer
    filter_fields = ('file_resource__md5', 'file_resource',
                     'storage__name',)


class DeploymentViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.Deployment.objects.all()
    serializer_class = tantalus.api.serializers.DeploymentSerializer


class FileTransferViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.FileTransfer.objects.all()
    serializer_class = tantalus.api.serializers.FileTransferSerializer


class GSCQueryViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.GSCQuery.objects.all()
    serializer_class = tantalus.api.serializers.GSCQuerySerializer


class MD5CheckViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.MD5Check.objects.all()
    serializer_class = tantalus.api.serializers.MD5CheckSerializer


