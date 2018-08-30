from rest_framework import viewsets, mixins
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from django_filters import rest_framework as filters
import tantalus.models
import tantalus.api.serializers
import tantalus.tasks
from tantalus.api.permissions import IsOwnerOrReadOnly
from rest_framework import permissions


class RestrictedQueryMixin(object):
    """Cause view to fail on invalid filter query parameter.

    Thanks to rrauenza on Stack Overflow for their post here:
    https://stackoverflow.com/questions/27182527/how-can-i-stop-django-rest-framework-to-show-all-records-if-query-parameter-is-w/50957733#50957733
    """
    def get_queryset(self):
        paging = set(['limit', 'offset', 'page', 'page_size'])

        qs = super(RestrictedQueryMixin, self).get_queryset()

        if hasattr(self, 'filter_fields') and hasattr(self, 'filter_class'):
            raise RuntimeError("%s has both filter_fields and filter_class" % self)

        if hasattr(self, 'filter_class'):
            filter_class = getattr(self, 'filter_class', None)
            filters = set(filter_class.get_filters().keys())
        elif hasattr(self, 'filter_fields'):
            filters = set(getattr(self, 'filter_fields', []))
        else:
            filters = set()

        for key in self.request.GET.keys():
            if key in paging:
                continue
            if key not in filters:
                return qs.none()

        return qs


class OwnerEditModelViewSet(viewsets.ModelViewSet):
    permission_classes = (
        permissions.IsAuthenticatedOrReadOnly,
        IsOwnerOrReadOnly,)
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return self.serializer_class_readonly
        return self.serializer_class_readwrite


class SampleFilter(filters.FilterSet):
    """Support specific filters for Samples."""

    class Meta:
        model = tantalus.models.Sample
        fields = {
            'id': ['exact', 'in'],
            'sample_id': ['exact', 'in'],
            'sequencedataset__id': ['exact', 'in', 'isnull'],
        }

    def __init__(self, *args, **kwargs):
        super(SampleFilter, self).__init__(*args, **kwargs)
        self.filters['sequencedataset__id'].label = 'Has SequenceDataset'
        self.filters['sequencedataset__id__in'].label = 'Has SequenceDataset in'
        self.filters['sequencedataset__id__isnull'].label = 'Has no SequenceDatasets'


class SampleViewSet(RestrictedQueryMixin, viewsets.ReadOnlyModelViewSet):
    queryset = tantalus.models.Sample.objects.all()
    serializer_class = tantalus.api.serializers.SampleSerializer
    filter_class = SampleFilter


class FileResourceViewSet(RestrictedQueryMixin, OwnerEditModelViewSet):
    queryset = tantalus.models.FileResource.objects.all()
    serializer_class_readonly = tantalus.api.serializers.FileResourceSerializerRead
    serializer_class_readwrite = tantalus.api.serializers.FileResourceSerializer
    filter_fields = ('id', 'filename')


class SequenceFileInfoViewSet(RestrictedQueryMixin, OwnerEditModelViewSet):
    queryset = tantalus.models.SequenceFileInfo.objects.all()
    serializer_class_readonly = tantalus.api.serializers.SequenceFileInfoSerializer
    serializer_class_readwrite = tantalus.api.serializers.SequenceFileInfoSerializer
    filter_fields = ('id',)


class DNALibraryViewSet(RestrictedQueryMixin, OwnerEditModelViewSet):
    queryset = tantalus.models.DNALibrary.objects.all()
    serializer_class_readonly = tantalus.api.serializers.DNALibrarySerializer
    serializer_class_readwrite = tantalus.api.serializers.DNALibrarySerializer
    filter_fields = ('id', 'library_id')


class SequencingLaneViewSet(RestrictedQueryMixin, OwnerEditModelViewSet):
    queryset = tantalus.models.SequencingLane.objects.all()
    serializer_class_readonly = tantalus.api.serializers.SequencingLaneSerializer
    serializer_class_readwrite = tantalus.api.serializers.SequencingLaneSerializer
    filter_fields = ('id', 'dna_library_id', 'flowcell_id', 'lane_number')


class SequenceDatasetViewSet(OwnerEditModelViewSet):
    queryset = tantalus.models.SequenceDataset.objects.all()
    serializer_class_readonly = tantalus.api.serializers.SequenceDatasetSerializerRead
    serializer_class_readwrite = tantalus.api.serializers.SequenceDatasetSerializer
    filter_fields = ('library__library_id', 'sample__sample_id',)


class StorageViewSet(RestrictedQueryMixin, viewsets.ReadOnlyModelViewSet):
    queryset = tantalus.models.Storage.objects.all()
    serializer_class = tantalus.api.serializers.StorageSerializer
    filter_fields = ('name',)


class ServerStorageViewSet(RestrictedQueryMixin, viewsets.ReadOnlyModelViewSet):
    queryset = tantalus.models.ServerStorage.objects.all()
    serializer_class = tantalus.api.serializers.ServerStorageSerializer
    filter_fields = ('name',)


class AzureBlobStorageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = tantalus.models.AzureBlobStorage.objects.all()
    serializer_class = tantalus.api.serializers.AzureBlobStorageSerializer


class FileInstanceViewSet(RestrictedQueryMixin, OwnerEditModelViewSet):
    queryset = tantalus.models.FileInstance.objects.all()
    serializer_class_readonly = tantalus.api.serializers.FileInstanceSerializerRead
    serializer_class_readwrite = tantalus.api.serializers.FileInstanceSerializer
    filter_fields = ('storage__name',)


class FileTransferViewSet(RestrictedQueryMixin, viewsets.ModelViewSet):
    queryset = tantalus.models.FileTransfer.objects.all()
    serializer_class = tantalus.api.serializers.FileTransferSerializer
    filter_fields = ('name', 'id',)


class MD5CheckViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.MD5Check.objects.all()
    serializer_class = tantalus.api.serializers.MD5CheckSerializer


class BRCImportFastqsViewSet(RestrictedQueryMixin, viewsets.ModelViewSet):
    queryset = tantalus.models.BRCFastqImport.objects.all()
    serializer_class = tantalus.api.serializers.ImportBRCFastqsSerializer
    filter_fields = ('id', 'name')


class QueryGscWgsBamsViewSet(RestrictedQueryMixin, viewsets.ModelViewSet):
    queryset = tantalus.models.GscWgsBamQuery.objects.all()
    serializer_class = tantalus.api.serializers.QueryGscWgsBamsSerializer
    filter_fields = ('id', 'name')


class QueryGscDlpPairedFastqsViewSet(RestrictedQueryMixin, viewsets.ModelViewSet):
    queryset = tantalus.models.GscDlpPairedFastqQuery.objects.all()
    serializer_class = tantalus.api.serializers.QueryGscDlpPairedFastqsSerializer
    filter_fields = ('dlp_library_id', 'id', 'name')


class ImportDlpBamViewSet(RestrictedQueryMixin, viewsets.ModelViewSet):
    queryset = tantalus.models.ImportDlpBam.objects.all()
    serializer_class = tantalus.api.serializers.ImportDlpBamSerializer
    filter_fields = ('id', 'name')


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
                queue=transfer.get_queue_name())
        serializer = tantalus.api.serializers.FileTransferSerializer(transfer)
        return Response(serializer.data)


class DatasetsTag(RestrictedQueryMixin, viewsets.ModelViewSet):
    """
    To tag datasets in this endpoint, use the following JSON format to POST:
        { "name": "test_api_tag", "sequencedataset_set": [1, 2, 3, 4] }
    """
    queryset = tantalus.models.Tag.objects.all()
    serializer_class = tantalus.api.serializers.DatasetTagSerializer
    filter_fields = ('name',)


# TODO: move this
from tantalus.backend.serializers import *

class AddDataView(viewsets.ViewSet):
    def create(self, request, format=None):
        """Create model entries from request data.

        This expects the request data to be in the form

        {"tag": "tag name", # or null
         "model_dictionaries": [{ ... }, { ... }, ... ]
        }

        The model_dictionaries array of dictionaries is complicated.
        Easiest way to get a handle on it is to trace through this
        function and the get_or_create_serialize*.
        """
        with django.db.transaction.atomic():
            tag = None

            if request.data['tag']:
                tag, _ = tantalus.models.Tag.objects.get_or_create(name=request.data['tag'])

            for dictionary in request.data['model_dictionaries']:
                if dictionary['model'] == 'FileInstance':
                    dictionary.pop('model')
                    get_or_create_serialize_file_instance(dictionary)

                elif dictionary['model'] == 'SequenceDataset':
                    dictionary.pop('model')
                    dataset = get_or_create_serialize_sequence_dataset(dictionary)
                    if tag:
                        dataset.tags.add(tag)

                elif dictionary['model'] == 'SequenceLane':
                    dictionary.pop('model')
                    get_or_create_serialize_sequence_lane(dictionary)

                else:
                    raise ValueError('model type {} not supported'.format(dictionary['model']))

        return Response('success', status=201)


class ResultDatasetsViewSet(RestrictedQueryMixin, OwnerEditModelViewSet):
    queryset = tantalus.models.ResultsDataset.objects.all()
    serializer_class_readonly = tantalus.api.serializers.ResultDatasetSerializer
    serializer_class_readwrite = tantalus.api.serializers.ResultDatasetSerializer
    filter_fields = ('id', 'owner', 'name', 'samples', 'analysis')


class AnalysisViewSet(RestrictedQueryMixin, OwnerEditModelViewSet):
    queryset = tantalus.models.Analysis.objects.all()
    serializer_class_readonly = tantalus.api.serializers.AnalysisSerializer
    serializer_class_readwrite = tantalus.api.serializers.AnalysisSerializer
    filter_fields = ('id', 'name', 'jira_ticket', 'last_updated')
