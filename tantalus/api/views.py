from rest_framework import viewsets
import tantalus.models
import tantalus.api.serializers


class SampleViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.Sample.objects.all()
    serializer_class = tantalus.api.serializers.SampleSerializer
    filter_fields = ('sample_id',)


class SequenceDataFileViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.SequenceDataFile.objects.all()
    serializer_class = tantalus.api.serializers.SequenceDataFileSerializer


class IndexedReadsViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.IndexedReads.objects.all()
    serializer_class = tantalus.api.serializers.IndexedReadsSerializer
    filter_fields = ('dnalibrary',)


class DNALibraryViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.DNALibrary.objects.all()
    serializer_class = tantalus.api.serializers.DNALibrarySerializer


class DNALibrarySubsetViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.DNALibrarySubset.objects.all()
    serializer_class = tantalus.api.serializers.DNALibrarySubsetSerializer


class SequenceLaneViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.SequenceLane.objects.all()
    serializer_class = tantalus.api.serializers.SequenceLaneSerializer


class PairedFastqFilesViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.PairedFastqFiles.objects.all()
    serializer_class = tantalus.api.serializers.PairedFastqFilesSerializer


class BamFileViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.BamFile.objects.all()
    serializer_class = tantalus.api.serializers.BamFileSerializer


class AzureBlobFileInstanceViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.AzureBlobFileInstance.objects.all()
    serializer_class = tantalus.api.serializers.AzureBlobFileInstanceSerializer


class ServerFileInstanceViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.ServerFileInstance.objects.all()
    serializer_class = tantalus.api.serializers.ServerFileInstanceSerializer



