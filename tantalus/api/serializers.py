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


class AbstractDataSetSerializer(serializers.ModelSerializer):
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


class SingleEndFastqFileSerializer(serializers.ModelSerializer):
    lanes = SequenceLaneSerializer(many=True)
    dna_sequences = DNASequencesSerializer()

    class Meta:
        model = tantalus.models.SingleEndFastqFile
        exclude = ['polymorphic_ctype']


class PairedEndFastqFilesSerializer(serializers.ModelSerializer):
    lanes = SequenceLaneSerializer(many=True)
    dna_sequences = DNASequencesSerializer()
    reads_1_file = FileResourceSerializer()
    reads_2_file = FileResourceSerializer()

    class Meta:
        model = tantalus.models.PairedEndFastqFiles
        exclude = ['polymorphic_ctype']


class BamFileSerializer(serializers.ModelSerializer):
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
    def create(self, validated_data):
        instance = self.Meta.model(**validated_data)
        instance.full_clean()
        instance.save()
        tantalus.tasks.transfer_files_task.apply_async(
            args=(instance.id,),
            queue=instance.get_transfer_queue_name())
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


class DatasetTagSerializer(serializers.Serializer):
    tag = serializers.CharField()
    datasets = serializers.PrimaryKeyRelatedField(many=True, queryset=tantalus.models.AbstractDataSet.objects.all())

    def create(self, validated_data):
        tag_name = validated_data['tag']
        datasets = validated_data['datasets']
        tag, created = tantalus.models.Tag.objects.get_or_create(name=tag_name)
        tag.abstractdataset_set.clear()
        tag.abstractdataset_set.add(*datasets)
        return validated_data

