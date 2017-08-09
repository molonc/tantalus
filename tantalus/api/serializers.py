from rest_framework import serializers
import tantalus.models
from taggit_serializer.serializers import (
    TagListSerializerField,
    TaggitSerializer)


class SampleSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.Sample
        fields = '__all__'


class SequenceDataFileSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.SequenceDataFile
        fields = '__all__'


class DNALibrarySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.DNALibrary
        fields = '__all__'


class DNASequencesSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.DNASequences
        fields = '__all__'


class SequenceLaneSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.SequenceLane
        fields = '__all__'


class SequenceDatasetSerializer(TaggitSerializer, serializers.HyperlinkedModelSerializer):
    tags = TagListSerializerField()
    class Meta:
        model = tantalus.models.SequenceDataset
        fields = '__all__'


class SingleEndFastqFileSerializer(TaggitSerializer, serializers.HyperlinkedModelSerializer):
    tags = TagListSerializerField()
    class Meta:
        model = tantalus.models.SingleEndFastqFile
        fields = '__all__'


class PairedEndFastqFilesSerializer(TaggitSerializer, serializers.HyperlinkedModelSerializer):
    tags = TagListSerializerField()
    class Meta:
        model = tantalus.models.PairedEndFastqFiles
        fields = '__all__'


class BamFileSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.BamFile
        fields = '__all__'


class StorageSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.Storage
        fields = '__all__'


class ServerStorageSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.ServerStorage
        fields = '__all__'


class AzureBlobStorageSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.AzureBlobStorage
        fields = '__all__'


class FileInstanceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.FileInstance
        fields = '__all__'


class DeploymentSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.Deployment
        fields = '__all__'


class FileTransferSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.FileTransfer
        fields = '__all__'


