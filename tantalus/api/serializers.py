from django.db import transaction
from rest_framework import serializers
from taggit_serializer.serializers import (
    TagListSerializerField,
    TaggitSerializer)
from rest_framework.validators import UniqueValidator, UniqueTogetherValidator
from rest_framework.exceptions import ValidationError
from tantalus.utils import create_deployment_file_transfers, DeploymentNotCreated
from tantalus.tasks import transfer_file, create_subdirectories
import tantalus.models
from celery import chain


class SampleSerializer(serializers.ModelSerializer):
    sample_id = serializers.CharField(
        validators=[
            UniqueValidator(queryset=tantalus.models.Sample.objects.all())
        ]
    )

    class Meta:
        model = tantalus.models.Sample
        fields = '__all__'


class FileResourceSerializer(serializers.ModelSerializer):
    md5 = serializers.CharField(
        validators=[
            UniqueValidator(queryset=tantalus.models.FileResource.objects.all())
        ]
    )

    class Meta:
        model = tantalus.models.FileResource
        fields = '__all__'


class DNALibrarySerializer(serializers.ModelSerializer):
    library_id = serializers.CharField(
        validators=[
            UniqueValidator(queryset=tantalus.models.DNALibrary.objects.all())
        ]
    )

    class Meta:
        model = tantalus.models.DNALibrary
        fields = '__all__'


class DNASequencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = tantalus.models.DNASequences
        fields = '__all__'
        validators = [
            UniqueTogetherValidator(
                queryset=tantalus.models.DNASequences.objects.all(),
                fields=('dna_library', 'index_sequence')
            )
        ]


class SequenceLaneSerializer(serializers.ModelSerializer):
    class Meta:
        model = tantalus.models.SequenceLane
        fields = '__all__'
        validators = [
            UniqueTogetherValidator(
                queryset=tantalus.models.SequenceLane.objects.all(),
                fields=('flowcell_id', 'lane_number')
            )
        ]


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
        #TODO: add validator


class PairedEndFastqFilesReadSerializer(TaggitSerializer, serializers.ModelSerializer):
    tags = TagListSerializerField()
    lanes = SequenceLaneSerializer(many=True)
    dna_sequences = DNASequencesSerializer()

    class Meta:
        model = tantalus.models.PairedEndFastqFiles
        exclude = ['polymorphic_ctype']


class PairedEndFastqFilesSerializer(TaggitSerializer, serializers.ModelSerializer):
    tags = TagListSerializerField()

    class Meta:
        model = tantalus.models.PairedEndFastqFiles
        exclude = ['polymorphic_ctype']
        validators = [
            UniqueTogetherValidator(
                queryset=tantalus.models.PairedEndFastqFiles.objects.all(),
                fields=('reads_1_file', 'reads_2_file')
            )
        ]


class BamFileSerializer(TaggitSerializer, serializers.ModelSerializer):
    tags = TagListSerializerField()
    lanes = SequenceLaneSerializer(many=True)
    dna_sequences = DNASequencesSerializer()

    class Meta:
        model = tantalus.models.BamFile
        exclude = ['polymorphic_ctype']
        validators = [
            UniqueTogetherValidator(
                queryset=tantalus.models.BamFile.objects.all(),
                fields=('bam_file', 'bam_index_file')
            )
        ]


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
    # generic_url = serializers.SerializerMethodField(method_name='_get_generic_url')

    class Meta:
        model = tantalus.models.ServerStorage
        exclude = ['polymorphic_ctype']

    def to_representation(self, obj):
        res = super(ServerStorageSerializer, self).to_representation(obj)
        return res


class AzureBlobStorageSerializer(serializers.ModelSerializer):
    class Meta:
        model = tantalus.models.AzureBlobStorage
        exclude = ['polymorphic_ctype']


class FileInstanceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.FileInstance
        fields = '__all__'
        validators = [
            UniqueTogetherValidator(
                queryset=tantalus.models.FileInstance.objects.all(),
                fields=('file_resource', 'storage')
            )
        ]


class DeploymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = tantalus.models.Deployment
        fields = '__all__'

    def create(self, validated_data):

        def start_async_transfers(files_to_transfer):
            for file_transfer in files_to_transfer:
                to_storage_type = file_transfer.to_storage.__class__.__name__
                if to_storage_type == 'ServerStorage':
                    # TODO: only 1 mkdir task is allowed to run at a time?
                    chain(
                        create_subdirectories.signature((file_transfer.id,), immutable=True).set(queue=instance.to_storage.name),
                        transfer_file.signature((file_transfer.id,), immutable=True).set(queue=instance.from_storage.name)
                    ).apply_async()
                else:
                    transfer_file.apply_async(args=(file_transfer.id,), queue=instance.from_storage.name)

        try:
            with transaction.atomic():
                # remove many2many relationships from validated_data
                datasets = validated_data.pop('datasets', [])
                file_transfers = validated_data.pop('file_transfers', [])

                instance = tantalus.models.Deployment(**validated_data)
                instance.save()
                instance.datasets = datasets
                instance.file_transfers = file_transfers

                files_to_transfer = create_deployment_file_transfers(instance)

                transaction.on_commit(lambda: start_async_transfers(files_to_transfer))
            return instance

        except DeploymentNotCreated as e:
            # TODO: construct JSON response
            raise DeploymentNotCreated(str(e))


class FileTransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = tantalus.models.FileTransfer
        fields = '__all__'
