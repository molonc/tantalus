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
    def to_representation(self, obj):
        if isinstance(obj, tantalus.models.SingleEndFastqFile):
            return SingleEndFastqFileSerializer(obj, context=self.context).to_representation(obj)
        elif isinstance(obj, tantalus.models.PairedEndFastqFiles):
           return PairedEndFastqFilesSerializer(obj, context=self.context).to_representation(obj)
        elif isinstance(obj, tantalus.models.BamFile):
           return BamFileSerializer(obj, context=self.context).to_representation(obj)
        return super(SequenceDatasetSerializer, self).to_representation(obj)


class SingleEndFastqFileSerializer(TaggitSerializer, serializers.HyperlinkedModelSerializer):
    tags = TagListSerializerField()
    class Meta:
        model = tantalus.models.SingleEndFastqFile
        exclude = ['polymorphic_ctype']


class PairedEndFastqFilesSerializer(TaggitSerializer, serializers.HyperlinkedModelSerializer):
    tags = TagListSerializerField()
    class Meta:
        model = tantalus.models.PairedEndFastqFiles
        exclude = ['polymorphic_ctype']


class BamFileSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.BamFile
        exclude = ['polymorphic_ctype']


class StorageSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.Storage
        exclude = ['polymorphic_ctype']
    def to_representation(self, obj):
        if isinstance(obj, tantalus.models.ServerStorage):
            return ServerStorageSerializer(obj, context=self.context).to_representation(obj)
        elif isinstance(obj, tantalus.models.AzureBlobStorage):
           return AzureBlobStorageSerializer(obj, context=self.context).to_representation(obj)
        return super(StorageSerializer, self).to_representation(obj)


class ServerStorageSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.ServerStorage
        exclude = ['polymorphic_ctype']


class AzureBlobStorageSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.AzureBlobStorage
        exclude = ['polymorphic_ctype']


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


