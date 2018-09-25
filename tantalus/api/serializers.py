from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers

import tantalus.models
import tantalus.tasks


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
    storage_directory = serializers.SerializerMethodField()
    storage_type = serializers.CharField(read_only=True)

    def get_storage_directory(self, obj):
        return obj.get_storage_directory()

    class Meta:
        model = tantalus.models.ServerStorage
        fields = ('id', 'storage_type', 'name', 'storage_directory')


class AzureBlobStorageSerializer(serializers.ModelSerializer):
    storage_container = serializers.SerializerMethodField()
    storage_type = serializers.CharField(read_only=True)

    def get_storage_container(self, obj):
        return obj.get_storage_container()

    class Meta:
        model = tantalus.models.AzureBlobStorage
        fields = (
            'id',
            'storage_type',
            'name',
            'storage_account',
            'storage_container',
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
        return tantalus.models.FileType.objects.get(name=data)


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


class DNALibrarySerializer(serializers.ModelSerializer):
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


class SimpleTaskSerializer(serializers.ModelSerializer):
    name = serializers.CharField()
    running = serializers.BooleanField(read_only=True)
    finished = serializers.BooleanField(read_only=True)
    success = serializers.BooleanField(read_only=True)
    state = serializers.CharField(read_only=True)


class FileTransferSerializer(SimpleTaskSerializer):
    class Meta:
        model = tantalus.models.FileTransfer
        fields = '__all__'
    def create(self, validated_data):
        with transaction.atomic():
            instance = self.Meta.model(**validated_data)
            instance.full_clean()
            instance.save()
            transaction.on_commit(lambda: tantalus.tasks.transfer_files_task.apply_async(
                args=(instance.id,),
                queue=instance.get_queue_name()))
        return instance


class ImportBRCFastqsSerializer(SimpleTaskSerializer):
    class Meta:
        model = tantalus.models.BRCFastqImport
        fields = '__all__'
    def create(self, validated_data):
        instance = tantalus.models.BRCFastqImport(**validated_data)
        instance.full_clean()
        instance.save()
        tantalus.tasks.import_brc_fastqs_task.apply_async(
            args=(instance.id,),
            queue=instance.storage.get_db_queue_name())
        return instance


class MD5CheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = tantalus.models.MD5Check
        fields = '__all__'


class QueryGscSerializer(SimpleTaskSerializer):
    def create(self, validated_data):
        storage = get_object_or_404(tantalus.models.ServerStorage, name='gsc')
        instance = self.Meta.model(**validated_data)
        instance.full_clean()
        instance.save()
        self.celery_task.apply_async(
            args=(instance.id,),
            queue=storage.get_db_queue_name())
        return instance


class QueryGscWgsBamsSerializer(QueryGscSerializer):
    celery_task = tantalus.tasks.query_gsc_wgs_bams_task
    class Meta:
        model = tantalus.models.GscWgsBamQuery
        fields = '__all__'


class QueryGscDlpPairedFastqsSerializer(QueryGscSerializer):
    celery_task = tantalus.tasks.query_gsc_dlp_paired_fastqs_task
    class Meta:
        model = tantalus.models.GscDlpPairedFastqQuery
        fields = '__all__'


class ImportDlpBamSerializer(SimpleTaskSerializer):
    celery_task = tantalus.tasks.import_dlp_bams_task
    class Meta:
        model = tantalus.models.ImportDlpBam
        fields = '__all__'
    def update(self, instance, validated_data):
        self.Meta.model.objects.update_or_create(id=instance.id, **validated_data)
        instance.full_clean()
        instance.save()
        self.celery_task.apply_async(
            args=(instance.id,),
            queue=instance.get_queue_name())
        return instance
    def create(self, validated_data):
        instance = self.Meta.model(**validated_data)
        instance.full_clean()
        instance.save()
        self.celery_task.apply_async(
            args=(instance.id,),
            queue=instance.get_queue_name())
        return instance


class DatasetTagSerializer(serializers.ModelSerializer):
    """Serializer for tags."""
    sequencedataset_set = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=tantalus.models.SequenceDataset.objects.all(),)

    class Meta:
        model = tantalus.models.Tag
        fields = ('id', 'name', 'sequencedataset_set')


class ResultDatasetSerializer(serializers.ModelSerializer):
    class Meta:
        model = tantalus.models.ResultsDataset
        fields = '__all__'


class AnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = tantalus.models.Analysis
        fields = '__all__'
