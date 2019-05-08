from django.db import models
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
import rest_framework.exceptions
from rest_framework import viewsets, mixins
from rest_framework import permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from tantalus.api.permissions import IsOwnerOrReadOnly
import tantalus.api.serializers
from tantalus.api.filters import (
    AnalysisFilter,
    DNALibraryFilter,
    FileInstanceFilter,
    FileResourceFilter,
    PatientFilter,
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


class RestrictedQueryMixin(object):
    """Cause view to fail on invalid filter query parameter.

    Thanks to rrauenza on Stack Overflow for their post here:
    https://stackoverflow.com/questions/27182527/how-can-i-stop-django-rest-framework-to-show-all-records-if-query-parameter-is-w/50957733#50957733
    """
    def get_queryset(self):
        non_filter_params = set(['limit', 'offset', 'page', 'page_size', 'format'])

        qs = super(RestrictedQueryMixin, self).get_queryset().order_by('id')

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
        permissions.IsAuthenticated,)
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return self.serializer_class_readonly
        return self.serializer_class_readwrite


class SampleViewSet(RestrictedQueryMixin, viewsets.ModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    queryset = tantalus.models.Sample.objects.all()
    serializer_class = tantalus.api.serializers.SampleSerializer
    filter_class = SampleFilter


class PatientViewSet(RestrictedQueryMixin, viewsets.ModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    queryset = tantalus.models.Patient.objects.all()
    serializer_class = tantalus.api.serializers.PatientSerializer
    filter_class = PatientFilter


class FileResourceViewSet(RestrictedQueryMixin, OwnerEditModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    queryset = tantalus.models.FileResource.objects.all()
    serializer_class_readonly = tantalus.api.serializers.FileResourceSerializerRead
    serializer_class_readwrite = tantalus.api.serializers.FileResourceSerializer
    filter_class = FileResourceFilter


class FileResourceDetail(RestrictedQueryMixin, OwnerEditModelViewSet):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    queryset = tantalus.models.FileResource.objects.all()
    serializer_class_readonly = tantalus.api.serializers.FileResourceInstancesSerilizer
    serializer_class_readwrite = tantalus.api.serializers.FileResourceInstancesSerilizer


class SequenceFileInfoViewSet(RestrictedQueryMixin, OwnerEditModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    queryset = tantalus.models.SequenceFileInfo.objects.all()
    serializer_class_readonly = tantalus.api.serializers.SequenceFileInfoSerializer
    serializer_class_readwrite = tantalus.api.serializers.SequenceFileInfoSerializer
    filter_class = SequenceFileInfoFilter


class DNALibraryViewSet(RestrictedQueryMixin, OwnerEditModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    queryset = tantalus.models.DNALibrary.objects.all()
    serializer_class_readonly = tantalus.api.serializers.DNALibrarySerializer
    serializer_class_readwrite = tantalus.api.serializers.DNALibrarySerializer
    filter_class = DNALibraryFilter


class SequencingLaneViewSet(RestrictedQueryMixin, OwnerEditModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    queryset = tantalus.models.SequencingLane.objects.all()
    serializer_class_readonly = tantalus.api.serializers.SequencingLaneSerializer
    serializer_class_readwrite = tantalus.api.serializers.SequencingLaneSerializer
    filter_class = SequencingLaneFilter


class SequenceDatasetViewSet(RestrictedQueryMixin, OwnerEditModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    queryset = tantalus.models.SequenceDataset.objects.all()
    serializer_class_readonly = tantalus.api.serializers.SequenceDatasetSerializerRead
    serializer_class_readwrite = tantalus.api.serializers.SequenceDatasetSerializer
    filter_class = SequenceDatasetFilter

    def destroy(self, request, pk=None):
        """Delete all associated file resources too."""
        # Delete the file resources
        this_dataset = get_object_or_404(self.queryset, pk=pk)
        for file_resource in this_dataset.file_resources.all():
            for file_instance in file_resource.fileinstance_set.all():
                file_instance.is_deleted = True
                file_instance.save()

        # Call the parent constructor
        return super(SequenceDatasetViewSet, self).destroy(request, pk)


class StorageViewSet(RestrictedQueryMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    queryset = tantalus.models.Storage.objects.all()
    serializer_class = tantalus.api.serializers.StorageSerializer
    filter_class = StorageFilter


class ServerStorageViewSet(RestrictedQueryMixin, viewsets.ModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    queryset = tantalus.models.ServerStorage.objects.all()
    serializer_class = tantalus.api.serializers.ServerStorageSerializer
    filter_class = ServerStorageFilter


class AzureBlobStorageViewSet(RestrictedQueryMixin, viewsets.ModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    queryset = tantalus.models.AzureBlobStorage.objects.all()
    serializer_class = tantalus.api.serializers.AzureBlobStorageSerializer


class FileInstanceViewSet(RestrictedQueryMixin, OwnerEditModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    queryset = tantalus.models.FileInstance.objects.all()
    serializer_class_readonly = tantalus.api.serializers.FileInstanceSerializerRead
    serializer_class_readwrite = tantalus.api.serializers.FileInstanceSerializer
    filter_class = FileInstanceFilter


class Tag(RestrictedQueryMixin, viewsets.ModelViewSet):
    """
    To tag datasets in this endpoint, use the following JSON format to POST:
        { "name": "test_api_tag", "sequencedataset_set": [1, 2, 3, 4], "resultsdataset_set": [9, 10] }
    Note that a post will update an existing tag by adding it to the given datasets
    """
    permission_classes = (permissions.IsAuthenticated,)
    queryset = tantalus.models.Tag.objects.all()
    serializer_class = tantalus.api.serializers.TagSerializer
    filter_class = TagFilter


class ResultsDatasetViewSet(RestrictedQueryMixin, OwnerEditModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    queryset = tantalus.models.ResultsDataset.objects.all()
    serializer_class_readonly = tantalus.api.serializers.ResultsDatasetSerializerRead
    serializer_class_readwrite = tantalus.api.serializers.ResultsDatasetSerializer
    filter_class = ResultsDatasetFilter

    def destroy(self, request, pk=None):
        """Delete all associated file resources too."""
        # Delete the file resources
        this_dataset = get_object_or_404(self.queryset, pk=pk)
        for file_resource in this_dataset.file_resources.all():
            for file_instance in file_resource.fileinstance_set.all():
                file_instance.is_deleted = True
                file_instance.save()

        # Call the parent constructor
        return super(ResultsDatasetViewSet, self).destroy(request, pk)


class AnalysisViewSet(RestrictedQueryMixin, OwnerEditModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    queryset = tantalus.models.Analysis.objects.all().distinct()
    serializer_class_readonly = tantalus.api.serializers.AnalysisSerializer
    serializer_class_readwrite = tantalus.api.serializers.AnalysisSerializer
    filter_class = AnalysisFilter
