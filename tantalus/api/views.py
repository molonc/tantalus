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
    filter_fields = ('md5',)


class DNALibraryViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.DNALibrary.objects.all()
    serializer_class = tantalus.api.serializers.DNALibrarySerializer
    filter_fields = ('library_id',)


class DNASequencesViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.DNASequences.objects.all()
    serializer_class = tantalus.api.serializers.DNASequencesSerializer
    filter_fields = ('dna_library__library_id', 'dna_library__id', 'index_sequence',)


class SequenceLaneViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.SequenceLane.objects.all()
    serializer_class = tantalus.api.serializers.SequenceLaneSerializer
    filter_fields = ('flowcell_id', 'lane_number',)


class SequenceDatasetViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.SequenceDataset.objects.all()
    serializer_class = tantalus.api.serializers.SequenceDatasetSerializer


class SingleEndFastqFileViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.SingleEndFastqFile.objects.all()
    serializer_class = tantalus.api.serializers.SingleEndFastqFileSerializer
    filter_fields = ('reads_file__md5', 'reads_file__id',)


class PairedEndFastqFilesViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.PairedEndFastqFiles.objects.all()
    serializer_class = tantalus.api.serializers.PairedEndFastqFilesSerializer
    filter_fields = ('reads_1_file__md5', 'reads_1_file__id',
                     'reads_2_file__md5', 'reads_2_file__id')


class BamFileViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.BamFile.objects.all()
    serializer_class = tantalus.api.serializers.BamFileSerializer
    filter_fields = ('bam_file__md5', 'bam_file__id'
                     'bam_index_file__md5', 'bam_index_file__id')


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
    filter_fields = ('file_resource__md5', 'file_resource__id',
                     'storage__name',)


class DeploymentViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.Deployment.objects.all()
    serializer_class = tantalus.api.serializers.DeploymentSerializer


class FileTransferViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.FileTransfer.objects.all()
    serializer_class = tantalus.api.serializers.FileTransferSerializer


