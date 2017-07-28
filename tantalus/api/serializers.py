from rest_framework import serializers
import tantalus.models


class SampleSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.Sample
        fields = '__all__'


class SequenceDataFileSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.SequenceDataFile
        fields = '__all__'


class IndexedReadsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.IndexedReads
        fields = '__all__'


class DNALibrarySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.DNALibrary
        fields = '__all__'


class DNALibrarySubsetSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.DNALibrarySubset
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


class ServerFileInstanceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.ServerFileInstance
        fields = '__all__'


class AzureBlobFileInstanceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.AzureBlobFileInstance
        fields = '__all__'


