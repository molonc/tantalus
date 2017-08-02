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


class DNALibraryViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.DNALibrary.objects.all()
    serializer_class = tantalus.api.serializers.DNALibrarySerializer


class DNASequencesViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.DNASequences.objects.all()
    serializer_class = tantalus.api.serializers.DNASequencesSerializer


class SequenceLaneViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.SequenceLane.objects.all()
    serializer_class = tantalus.api.serializers.SequenceLaneSerializer


class PairedFastqFilesViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.PairedFastqFiles.objects.all()
    serializer_class = tantalus.api.serializers.PairedFastqFilesSerializer


class BamFileViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.BamFile.objects.all()
    serializer_class = tantalus.api.serializers.BamFileSerializer


class ServerViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.Server.objects.all()
    serializer_class = tantalus.api.serializers.ServerSerializer


class ServerFileInstanceViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.ServerFileInstance.objects.all()
    serializer_class = tantalus.api.serializers.ServerFileInstanceSerializer


class AzureBlobFileInstanceViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.AzureBlobFileInstance.objects.all()
    serializer_class = tantalus.api.serializers.AzureBlobFileInstanceSerializer



