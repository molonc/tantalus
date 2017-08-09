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


class SequenceDatasetViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.SequenceDataset.objects.all()
    serializer_class = tantalus.api.serializers.SequenceDatasetSerializer


class SingleEndFastqFileViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.SingleEndFastqFile.objects.all()
    serializer_class = tantalus.api.serializers.SingleEndFastqFileSerializer


class PairedEndFastqFilesViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.PairedEndFastqFiles.objects.all()
    serializer_class = tantalus.api.serializers.PairedEndFastqFilesSerializer


class BamFileViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.BamFile.objects.all()
    serializer_class = tantalus.api.serializers.BamFileSerializer


class StorageViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.Storage.objects.all()
    serializer_class = tantalus.api.serializers.StorageSerializer


class ServerStorageViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.ServerStorage.objects.all()
    serializer_class = tantalus.api.serializers.ServerStorageSerializer


class AzureBlobStorageViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.AzureBlobStorage.objects.all()
    serializer_class = tantalus.api.serializers.AzureBlobStorageSerializer


class FileInstanceViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.FileInstance.objects.all()
    serializer_class = tantalus.api.serializers.FileInstanceSerializer


class DeploymentViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.Deployment.objects.all()
    serializer_class = tantalus.api.serializers.DeploymentSerializer


class FileTransferViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.FileTransfer.objects.all()
    serializer_class = tantalus.api.serializers.FileTransferSerializer


