from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from taggit_serializer.serializers import (
    TagListSerializerField,
    TaggitSerializer)

import tantalus.models
from tantalus.utils import start_file_transfers, validate_deployment, add_file_transfers, initialize_deployment
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

    def get_storage_directory(self, obj):
        return obj.get_storage_directory()

    class Meta:
        model = tantalus.models.ServerStorage
        fields = ('id', 'name', 'storage_directory')


class AzureBlobStorageSerializer(serializers.ModelSerializer):
    storage_container = serializers.SerializerMethodField()

    def get_storage_container(self, obj):
        return obj.get_storage_container()

    class Meta:
        model = tantalus.models.AzureBlobStorage
        fields = ('id', 'name', 'storage_account', 'storage_container')


class FileInstanceSerializer(serializers.ModelSerializer):
    filepath = serializers.SerializerMethodField()
    storage = StorageSerializer(read_only=True)

    def get_filepath(self, obj):
        return obj.get_filepath()

    class Meta:
        model = tantalus.models.FileInstance
        fields = '__all__'


class FileResourceSerializer(serializers.ModelSerializer):
    file_instances = FileInstanceSerializer(source='fileinstance_set', many=True, read_only=True)

    class Meta:
        model = tantalus.models.FileResource
        fields = '__all__'


class DNALibrarySerializer(serializers.ModelSerializer):
    class Meta:
        model = tantalus.models.DNALibrary
        fields = '__all__'


class DNASequencesSerializer(serializers.ModelSerializer):
    dna_library = DNALibrarySerializer()
    sample = SampleSerializer()

    class Meta:
        model = tantalus.models.DNASequences
        fields = '__all__'


class SequenceLaneSerializer(serializers.ModelSerializer):

    class Meta:
        model = tantalus.models.SequenceLane
        fields = '__all__'


class AbstractDataSetSerializer(TaggitSerializer, serializers.ModelSerializer):
    tags = TagListSerializerField()

    class Meta:
        model = tantalus.models.AbstractDataSet
        fields = '__all__'

    def to_representation(self, obj):
        if isinstance(obj, tantalus.models.SingleEndFastqFile):
            return SingleEndFastqFileSerializer(obj, context=self.context).to_representation(obj)

        elif isinstance(obj, tantalus.models.PairedEndFastqFiles):
            return PairedEndFastqFilesSerializer(obj, context=self.context).to_representation(obj)

        elif isinstance(obj, tantalus.models.BamFile):
            return BamFileSerializer(obj, context=self.context).to_representation(obj)

        return super(AbstractDataSetSerializer, self).to_representation(obj)


class SingleEndFastqFileSerializer(TaggitSerializer, serializers.ModelSerializer):
    tags = TagListSerializerField()
    lanes = SequenceLaneSerializer(many=True)
    dna_sequences = DNASequencesSerializer()

    class Meta:
        model = tantalus.models.SingleEndFastqFile
        exclude = ['polymorphic_ctype']


class PairedEndFastqFilesSerializer(TaggitSerializer, serializers.ModelSerializer):
    tags = TagListSerializerField()
    lanes = SequenceLaneSerializer(many=True)
    dna_sequences = DNASequencesSerializer()
    reads_1_file = FileResourceSerializer()
    reads_2_file = FileResourceSerializer()

    class Meta:
        model = tantalus.models.PairedEndFastqFiles
        exclude = ['polymorphic_ctype']


class BamFileSerializer(TaggitSerializer, serializers.ModelSerializer):
    tags = TagListSerializerField()
    lanes = SequenceLaneSerializer(many=True)
    dna_sequences = DNASequencesSerializer()
    bam_file = FileResourceSerializer()
    bam_index_file = FileResourceSerializer()

    class Meta:
        model = tantalus.models.BamFile
        exclude = ['polymorphic_ctype']


class SimpleTaskSerializer(serializers.ModelSerializer):
    running = serializers.BooleanField(read_only=True)
    finished = serializers.BooleanField(read_only=True)
    success = serializers.BooleanField(read_only=True)
    state = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)


class FileTransferSerializer(SimpleTaskSerializer):
    class Meta:
        model = tantalus.models.FileTransfer
        fields = '__all__'


class DeploymentSerializer(serializers.ModelSerializer):
    percent_finished = serializers.SerializerMethodField()

    def get_percent_finished(self, obj):
        return obj.get_percent_finished()

    percent_succeeded = serializers.SerializerMethodField()

    def get_percent_succeeded(self, obj):
        return obj.get_percent_succeeded()

    class Meta:
        model = tantalus.models.Deployment
        fields = '__all__'
        read_only_fields = ('running', 'finished', 'errors', 'file_transfers')

    def validate(self, data):
        from_storage = data['from_storage']
        to_storage = data['to_storage']
        datasets = data['datasets']

        validate_deployment(datasets, from_storage, to_storage, serializers.ValidationError)

        return data

    def save(self, **kwargs):
        with transaction.atomic():
            super(DeploymentSerializer, self).save(**kwargs)
            add_file_transfers(self.instance)
            if self.instance.start and not self.instance.running:
                initialize_deployment(deployment=self.instance)
                # Wrapped in an on_commit so that celery tasks do not get started before changes are saved to the database
                transaction.on_commit(lambda: start_file_transfers(deployment=self.instance))
            self.instance.save()
        return self.instance


class ImportBRCFastqsSerializer(SimpleTaskSerializer):
    def create(self, validated_data):
        instance = tantalus.models.BRCFastqImport(**validated_data)
        instance.full_clean()
        instance.save()
        tantalus.tasks.import_brc_fastqs_task.apply_async(
            args=(instance.id,),
            queue=instance.storage.get_db_queue_name())
        return instance

    class Meta:
        model = tantalus.models.BRCFastqImport
        fields = '__all__'


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

