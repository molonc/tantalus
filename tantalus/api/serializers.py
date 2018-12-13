from django.db import transaction
from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from rest_framework import serializers

import tantalus.models


class SampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = tantalus.models.Sample
        fields = '__all__'


class StorageSerializer(serializers.ModelSerializer):
    class Meta:
        model = tantalus.models.Storage
        exclude = ['polymorphic_ctype']

    def to_representation(self, obj):
        if isinstance(obj, tantalus.models.ServerStorage):
            return ServerStorageSerializer(obj, context=self.context).to_representation(obj)
        elif isinstance(obj, tantalus.models.AzureBlobStorage):
            return AzureBlobStorageSerializer(obj, context=self.context).to_representation(obj)
        return super(StorageSerializer, self).to_representation(obj)


class ServerStorageSerializer(serializers.ModelSerializer):
    prefix = serializers.SerializerMethodField()
    storage_type = serializers.CharField(read_only=True)

    def get_prefix(self, obj):
        return obj.get_prefix()

    class Meta:
        model = tantalus.models.ServerStorage
        fields = (
            'id',
            'storage_type',
            'name',
            'storage_directory',
            'prefix',
            'server_ip',
        )


class AzureBlobStorageSerializer(serializers.ModelSerializer):
    prefix = serializers.SerializerMethodField()
    storage_type = serializers.CharField(read_only=True)

    def get_prefix(self, obj):
        return obj.get_prefix()

    class Meta:
        model = tantalus.models.AzureBlobStorage
        fields = (
            'id',
            'storage_type',
            'name',
            'storage_account',
            'storage_container',
            'prefix',
            'credentials',
        )


class AzureBlobCredentialsSerializer(serializers.ModelSerializer):
    class Meta:
        model = tantalus.models.AzureBlobCredentials
        fields = '__all__'


class FileInstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = tantalus.models.FileInstance
        fields = '__all__'


class FileInstanceSerializerRead(serializers.ModelSerializer):
    filepath = serializers.SerializerMethodField()
    storage = StorageSerializer(read_only=True)

    def get_filepath(self, obj):
        return obj.get_filepath()

    class Meta:
        model = tantalus.models.FileInstance
        fields = '__all__'


class SequenceFileInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = tantalus.models.SequenceFileInfo
        fields = '__all__'


class FileTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = tantalus.models.FileType
        fields = '__all__'


class FileTypeField(serializers.Field):
    def to_representation(self, obj):
        return obj.name
    def to_internal_value(self, data):
        file_type, created = tantalus.models.FileType.objects.get_or_create(name=data)
        return file_type


class FileResourceSerializer(serializers.ModelSerializer):
    sequencefileinfo_set = SequenceFileInfoSerializer(read_only=True)
    file_type = FileTypeField()
    class Meta:
        model = tantalus.models.FileResource
        fields = '__all__'


class FileResourceSerializerRead(serializers.ModelSerializer):
    file_instances = FileInstanceSerializerRead(source='fileinstance_set', many=True, read_only=True)
    sequencefileinfo = SequenceFileInfoSerializer(read_only=True)
    file_type = FileTypeField()
    class Meta:
        model = tantalus.models.FileResource
        fields = '__all__'


class LibraryTypeField(serializers.ModelSerializer):
    def to_representation(self, obj):
        return obj.name
    def to_internal_value(self, data):
        return tantalus.models.LibraryType.objects.get(name=data)


class DNALibrarySerializer(serializers.ModelSerializer):
    library_type = LibraryTypeField()
    class Meta:
        model = tantalus.models.DNALibrary
        fields = '__all__'


class SequencingLaneSerializer(serializers.ModelSerializer):
    class Meta:
        model = tantalus.models.SequencingLane
        fields = '__all__'


class SequenceDatasetSerializer(serializers.ModelSerializer):
    class Meta:
        model = tantalus.models.SequenceDataset
        fields = '__all__'


class SequenceDatasetSerializerRead(serializers.ModelSerializer):
    sample = SampleSerializer()
    library = DNALibrarySerializer()
    sequence_lanes = SequencingLaneSerializer(many=True)
    class Meta:
        model = tantalus.models.SequenceDataset
        fields = '__all__'


class TagSerializer(serializers.ModelSerializer):
    """ Serializer for tags.
    Note that this serializer will always update by
    adding the tag to the given datasets.
    """
    sequencedataset_set = serializers.PrimaryKeyRelatedField(
        many=True,
        allow_null=True,
        required=False,
        queryset=tantalus.models.SequenceDataset.objects.all(),)

    resultsdataset_set = serializers.PrimaryKeyRelatedField(
        many=True,
        allow_null=True,
        required=False,
        queryset=tantalus.models.ResultsDataset.objects.all(),)

    class Meta:
        model = tantalus.models.Tag
        fields = ('id', 'name', 'sequencedataset_set', 'resultsdataset_set')

    def is_valid(self, raise_exception=False):
        if hasattr(self, 'initial_data'):
            try:
                obj = tantalus.models.Tag.objects.get(name=self.initial_data['name'])
            except (ObjectDoesNotExist, MultipleObjectsReturned):
                return super(TagSerializer, self).is_valid(raise_exception)
            else:
                self.instance = obj
                return super(TagSerializer, self).is_valid(raise_exception)
        else:
            return super(TagSerializer, self).is_valid(raise_exception)

    def update(self, instance, validated_data):
        for sequencedataset in validated_data.get('sequencedataset_set', ()):
            sequencedataset.tags.add(instance)
        for resultsdataset in validated_data.get('resultsdataset_set', ()):
            resultsdataset.tags.add(instance)
        return instance


class ResultDatasetSerializer(serializers.ModelSerializer):
    class Meta:
        model = tantalus.models.ResultsDataset
        fields = '__all__'


class AnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = tantalus.models.Analysis
        fields = '__all__'
