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


