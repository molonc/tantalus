from rest_framework import serializers
import tantalus.models


class SequenceFileResourceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.SequenceFileResource
        fields = '__all__'


class IndexedReadsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.IndexedReads
        fields = '__all__'


class SequenceLaneSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.SequenceLane
        fields = '__all__'


class PairedFastqFilesSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.PairedFastqFiles
        fields = '__all__'


class BamFileSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.BamFile
        fields = '__all__'


class ServerStorageSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.ServerStorage
        fields = '__all__'


class AzureBlobStorageSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.AzureBlobStorage
        fields = '__all__'


class ServerBamFileInstanceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.ServerBamFileInstance
        fields = '__all__'


class ServerPairedFastqFilesInstanceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.ServerPairedFastqFilesInstance
        fields = '__all__'


