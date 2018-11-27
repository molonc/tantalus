from django.db import models
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
import rest_framework.exceptions
from rest_framework import viewsets, mixins
from rest_framework import permissions
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from tantalus.api.permissions import IsOwnerOrReadOnly
import tantalus.api.serializers
from tantalus.api.filters import (
    AnalysisFilter,
    AzureBlobCredentialsFilter,
    DNALibraryFilter,
    FileInstanceFilter,
    FileResourceFilter,
    ResultsDatasetFilter,
    SampleFilter,
    SequenceDatasetFilter,
    SequenceFileInfoFilter,
    SequencingLaneFilter,
    ServerStorageFilter,
    StorageFilter,
    TagFilter,
)
import tantalus.models
import tantalus.tasks


class RestrictedQueryMixin(object):
    """Cause view to fail on invalid filter query parameter.

    Thanks to rrauenza on Stack Overflow for their post here:
    https://stackoverflow.com/questions/27182527/how-can-i-stop-django-rest-framework-to-show-all-records-if-query-parameter-is-w/50957733#50957733
    """
    def get_queryset(self):
        non_filter_params = set(['limit', 'offset', 'page', 'page_size', 'format'])

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
            if key in non_filter_params:
                continue
            if key not in filters:
                raise rest_framework.exceptions.APIException(
                    'no filter %s' % key)

        return qs


class OwnerEditModelViewSet(viewsets.ModelViewSet):
    permission_classes = (
        permissions.IsAuthenticatedOrReadOnly,)
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return self.serializer_class_readonly
        return self.serializer_class_readwrite


class SampleViewSet(RestrictedQueryMixin, viewsets.ModelViewSet):
    queryset = tantalus.models.Sample.objects.all()
    serializer_class = tantalus.api.serializers.SampleSerializer
    filter_class = SampleFilter


class FileResourceViewSet(RestrictedQueryMixin, OwnerEditModelViewSet):
    queryset = tantalus.models.FileResource.objects.all()
    serializer_class_readonly = tantalus.api.serializers.FileResourceSerializerRead
    serializer_class_readwrite = tantalus.api.serializers.FileResourceSerializer
    filter_class = FileResourceFilter


class SequenceFileInfoViewSet(RestrictedQueryMixin, OwnerEditModelViewSet):
    queryset = tantalus.models.SequenceFileInfo.objects.all()
    serializer_class_readonly = tantalus.api.serializers.SequenceFileInfoSerializer
    serializer_class_readwrite = tantalus.api.serializers.SequenceFileInfoSerializer
    filter_class = SequenceFileInfoFilter


class DNALibraryViewSet(RestrictedQueryMixin, OwnerEditModelViewSet):
    queryset = tantalus.models.DNALibrary.objects.all()
    serializer_class_readonly = tantalus.api.serializers.DNALibrarySerializer
    serializer_class_readwrite = tantalus.api.serializers.DNALibrarySerializer
    filter_class = DNALibraryFilter


class SequencingLaneViewSet(RestrictedQueryMixin, OwnerEditModelViewSet):
    queryset = tantalus.models.SequencingLane.objects.all()
    serializer_class_readonly = tantalus.api.serializers.SequencingLaneSerializer
    serializer_class_readwrite = tantalus.api.serializers.SequencingLaneSerializer
    filter_class = SequencingLaneFilter


class SequenceDatasetViewSet(RestrictedQueryMixin, OwnerEditModelViewSet):
    queryset = tantalus.models.SequenceDataset.objects.all()
    serializer_class_readonly = tantalus.api.serializers.SequenceDatasetSerializerRead
    serializer_class_readwrite = tantalus.api.serializers.SequenceDatasetSerializer
    filter_class = SequenceDatasetFilter

    def destroy(self, request, pk=None):
        """Delete all associated file resources too."""
        # Delete the file resources
        this_dataset = get_object_or_404(self.queryset, pk=pk)
        this_dataset.file_resources.all().delete()

        # Call the parent constructor
        return super(SequenceDatasetViewSet, self).destroy(request, pk)


class StorageViewSet(RestrictedQueryMixin, viewsets.ReadOnlyModelViewSet):
    queryset = tantalus.models.Storage.objects.all()
    serializer_class = tantalus.api.serializers.StorageSerializer
    filter_class = StorageFilter


class ServerStorageViewSet(RestrictedQueryMixin, viewsets.ModelViewSet):
    queryset = tantalus.models.ServerStorage.objects.all()
    serializer_class = tantalus.api.serializers.ServerStorageSerializer
    filter_class = ServerStorageFilter


class AzureBlobStorageViewSet(RestrictedQueryMixin, viewsets.ModelViewSet):
    queryset = tantalus.models.AzureBlobStorage.objects.all()
    serializer_class = tantalus.api.serializers.AzureBlobStorageSerializer


class AzureBlobCredentialsViewSet(RestrictedQueryMixin, viewsets.ModelViewSet):
    queryset = tantalus.models.AzureBlobCredentials.objects.all()
    serializer_class = tantalus.api.serializers.AzureBlobCredentialsSerializer
    filter_class = AzureBlobCredentialsFilter


class FileInstanceViewSet(RestrictedQueryMixin, OwnerEditModelViewSet):
    queryset = tantalus.models.FileInstance.objects.all()
    serializer_class_readonly = tantalus.api.serializers.FileInstanceSerializerRead
    serializer_class_readwrite = tantalus.api.serializers.FileInstanceSerializer
    filter_class = FileInstanceFilter


class FileTransferViewSet(RestrictedQueryMixin, viewsets.ModelViewSet):
    queryset = tantalus.models.FileTransfer.objects.all()
    serializer_class = tantalus.api.serializers.FileTransferSerializer
    filter_fields = ('id', 'name')


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


class Tag(RestrictedQueryMixin, viewsets.ModelViewSet):
    """
    To tag datasets in this endpoint, use the following JSON format to POST:
        { "name": "test_api_tag", "sequencedataset_set": [1, 2, 3, 4] }
    """
    queryset = tantalus.models.Tag.objects.all()
    serializer_class = tantalus.api.serializers.TagSerializer
    filter_class = TagFilter


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
    filter_class = ResultsDatasetFilter

    def destroy(self, request, pk=None):
        """Delete all associated file resources too."""
        # Delete the file resources
        this_dataset = get_object_or_404(self.queryset, pk=pk)
        this_dataset.file_resources.all().delete()

        # Call the parent constructor
        super(ResultDatasetsViewSet, self).destroy(request, pk)


class AnalysisViewSet(RestrictedQueryMixin, OwnerEditModelViewSet):
    queryset = tantalus.models.Analysis.objects.all()
    serializer_class_readonly = tantalus.api.serializers.AnalysisSerializer
    serializer_class_readwrite = tantalus.api.serializers.AnalysisSerializer
    filter_class = AnalysisFilter
