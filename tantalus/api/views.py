from rest_framework import viewsets
import tantalus.models
import tantalus.api.serializers


class SequenceFileResourceViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.SequenceFileResource.objects.all()
    serializer_class = tantalus.api.serializers.SequenceFileResourceSerializer


class IndexedReadsViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.IndexedReads.objects.all()
    serializer_class = tantalus.api.serializers.IndexedReadsSerializer


class SequenceLaneViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.SequenceLane.objects.all()
    serializer_class = tantalus.api.serializers.SequenceLaneSerializer


class FastqFileViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.FastqFile.objects.all()
    serializer_class = tantalus.api.serializers.FastqFileSerializer


class BamFileViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.BamFile.objects.all()
    serializer_class = tantalus.api.serializers.BamFileSerializer


class ServerStorageViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.ServerStorage.objects.all()
    serializer_class = tantalus.api.serializers.ServerStorageSerializer


class AzureBlobStorageViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.AzureBlobStorage.objects.all()
    serializer_class = tantalus.api.serializers.AzureBlobStorageSerializer


class ServerBamFileInstanceViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.ServerBamFileInstance.objects.all()
    serializer_class = tantalus.api.serializers.ServerBamFileInstanceSerializer


class ServerFastqFileInstanceViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.ServerFastqFileInstance.objects.all()
    serializer_class = tantalus.api.serializers.ServerFastqFileInstanceSerializer





