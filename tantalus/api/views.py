from rest_framework import viewsets, mixins
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
import django_filters
import tantalus.models
import tantalus.api.serializers
import tantalus.tasks


class SampleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = tantalus.models.Sample.objects.all()
    serializer_class = tantalus.api.serializers.SampleSerializer
    filter_fields = ('sample_id',)


class FileResourceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = tantalus.models.FileResource.objects.all()
    serializer_class = tantalus.api.serializers.FileResourceSerializer


class DNALibraryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = tantalus.models.DNALibrary.objects.all()
    serializer_class = tantalus.api.serializers.DNALibrarySerializer
    filter_fields = ('library_id',)


class SequenceLaneViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = tantalus.models.SequenceLane.objects.all()
    serializer_class = tantalus.api.serializers.SequenceLaneSerializer
    filter_fields = ('flowcell_id', 'lane_number', 'dna_library__library_id')


class ReadGroupViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = tantalus.models.ReadGroup.objects.all()
    serializer_class = tantalus.api.serializers.ReadGroupSerializer


class AbstractDataSetViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = tantalus.models.AbstractDataSet.objects.all()
    serializer_class = tantalus.api.serializers.AbstractDataSetSerializer


class BCLFolderViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = tantalus.models.BCLFolder.objects.all()
    serializer_class = tantalus.api.serializers.BCLFolderSerializer


class SingleEndFastqFileViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = tantalus.models.SingleEndFastqFile.objects.all()
    serializer_class = tantalus.api.serializers.SingleEndFastqFileSerializer


class PairedEndFastqFilesFilterSet(django_filters.FilterSet):
    library_id = django_filters.CharFilter(name='read_groups__dna_library__library_id', distinct=True)
    index_sequence = django_filters.CharFilter(name='read_groups__index_sequence', distinct=True)
    class Meta:
        model = tantalus.models.PairedEndFastqFiles
        fields = ['library_id', 'index_sequence']


class PairedEndFastqFilesViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = tantalus.models.PairedEndFastqFiles.objects.all()
    filter_class = PairedEndFastqFilesFilterSet
    serializer_class = tantalus.api.serializers.PairedEndFastqFilesSerializer


class BamFileFilterSet(django_filters.FilterSet):
    library_id = django_filters.CharFilter(name='read_groups__dna_library__library_id', distinct=True)
    sample_id = django_filters.CharFilter(name='read_groups__sample__sample_id', distinct=True)
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


class FileTransferViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.FileTransfer.objects.all()
    serializer_class = tantalus.api.serializers.FileTransferSerializer
    filter_fields = ('name',)


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


class FileTransferRestart(APIView):
    def get(self, request, pk, format=None):
        transfer = tantalus.models.FileTransfer.objects.get(pk=pk)
        serializer = tantalus.api.serializers.FileTransferSerializer(transfer)
        return Response(serializer.data)

    def post(self, request, pk, format=None):
        transfer = tantalus.models.FileTransfer.objects.get(pk=pk)
        if not transfer.running:
            transfer.state = 'transfer files queued'
            transfer.finished = False
            transfer.save()
            tantalus.tasks.transfer_files_task.apply_async(
                args=(transfer.id,),
                queue=transfer.get_transfer_queue_name())
        serializer = tantalus.api.serializers.FileTransferSerializer(transfer)
        return Response(serializer.data)


class DatasetsTag(viewsets.ViewSet):
    """
    To tag datasets in this endpoint, use the following JSON format to POST:
        { "tag": "test_api_tag", "datasets": [1, 2, 3, 4] }
    """
    def list(self, request, format=None):
        tags = tantalus.models.Tag.objects.all().values_list('name', flat=True).distinct()
        tags = map(str, tags)
        data = {'tags': tags}
        return Response(data)

    def create(self, request, format=None):
        serializer = tantalus.api.serializers.DatasetTagSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data, status=201)


