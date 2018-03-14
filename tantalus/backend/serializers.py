import django
import os
import sys
from django.utils.six import BytesIO
from rest_framework import serializers
from rest_framework.parsers import JSONParser

from tantalus.models import Storage, Sample, DNALibrary, FileResource, FileInstance, SequenceLane, ReadGroup, BamFile, GscWgsBamQuery
from tantalus.utils import start_md5_checks


class GetCreateModelSerializer(serializers.ModelSerializer):
    def is_valid(self, raise_exception=False):
        if hasattr(self, 'initial_data'):
            # If we are instantiating with data={something}
            try:
                # Try to get or create the object in question
                obj, created = self.Meta.model.objects.get_or_create(**self.initial_data)
                self.instance = obj
                return True
            except django.core.exceptions.MultipleObjectsReturned:
                # Except not finding the object or the data being ambiguous
                # for defining it. Then validate the data as usual
                return super(GetCreateModelSerializer, self).is_valid(raise_exception)
            else:
                # If the object is found add it to the serializer. Then
                # validate the data as usual
                self.instance = obj
                return super(GetCreateModelSerializer, self).is_valid(raise_exception)
        else:
            # If the Serializer was instantiated with just an object, and no
            # data={something} proceed as usual 
            return super(GetCreateModelSerializer, self).is_valid(raise_exception)


class SampleSerializer(GetCreateModelSerializer):
    class Meta:
        model = Sample
        fields = ('sample_id', )


def get_or_create_serialize_sample(data):
    sample_serializer = SampleSerializer(data=data)
    sample_serializer.is_valid(raise_exception=True)
    return sample_serializer.instance.id


class DNALibrarySerializer(GetCreateModelSerializer):
    class Meta:
        model = DNALibrary
        fields = ('library_id', 'library_type', 'index_format')


def get_or_create_serialize_dna_library(data):
    dna_library_serializer = DNALibrarySerializer(data=data)
    dna_library_serializer.is_valid(raise_exception=True)
    return dna_library_serializer.instance.id


class FileResourceSerializer(GetCreateModelSerializer):
    class Meta:
        model = FileResource
        fields = ('size', 'created', 'file_type', 'read_end', 'compression', 'filename')


def get_or_create_serialize_file_resource(data):
    file_resource_serializer = FileResourceSerializer(data=data)
    file_resource_serializer.is_valid(raise_exception=True)
    return file_resource_serializer.instance.id


class SequenceLaneSerializer(GetCreateModelSerializer):
    class Meta:
        model = SequenceLane
        fields = ('flowcell_id', 'lane_number', 'sequencing_centre', 'sequencing_instrument', 'read_type')


def get_or_create_serialize_sequence_lane(data):
    sequence_lane_serializer = SequenceLaneSerializer(data=data)
    sequence_lane_serializer.is_valid(raise_exception=True)
    return sequence_lane_serializer.instance.id


class FileInstanceSerializer(GetCreateModelSerializer):
    class Meta:
        model = FileInstance
        fields = ('storage_id', 'file_resource_id', 'filename_override')


def get_or_create_serialize_file_instance(data):
    data['storage_id'] = Storage.objects.get(**data.pop('storage')).id
    data['file_resource_id'] = get_or_create_serialize_file_resource(data.pop('file_resource'))

    file_instance_serializer = FileInstanceSerializer(data=data)
    file_instance_serializer.is_valid(raise_exception=True)
    return file_instance_serializer.instance.id


class ReadGroupSerializer(GetCreateModelSerializer):
    class Meta:
        model = ReadGroup
        fields = ('sample_id', 'dna_library_id', 'index_sequence', 'sequence_lane_id', 'sequencing_library_id')


def get_or_create_serialize_read_group(data):
    data['sample_id'] = get_or_create_serialize_sample(data.pop('sample'))
    data['dna_library_id'] = get_or_create_serialize_dna_library(data.pop('dna_library'))
    data['sequence_lane_id'] = get_or_create_serialize_sequence_lane(data.pop('sequence_lane'))

    read_group_serializer = ReadGroupSerializer(data=data)
    read_group_serializer.is_valid(raise_exception=True)
    return read_group_serializer.instance.id


class BamFileSerializer(GetCreateModelSerializer):
    class Meta:
        model = BamFile
        fields = ('bam_file_id', 'bam_index_file_id', 'reference_genome', 'aligner')


def get_or_create_serialize_bam_file(data):
    data['bam_file_id'] = get_or_create_serialize_file_resource(data.pop('bam_file'))
    
    if 'bam_index_file' in data:
        data['bam_index_file_id'] = get_or_create_serialize_file_resource(data.pop('bam_index_file'))

    read_groups = data.pop('read_groups')
    bam_file_serializer = BamFileSerializer(data=data)
    bam_file_serializer.is_valid(raise_exception=True)

    for read_group in read_groups:
        bam_file_serializer.instance.read_groups.add(get_or_create_serialize_read_group(read_group))

    return bam_file_serializer.instance.id


def read_models(json_data_filename):
    with open(json_data_filename) as f:
        json_list = JSONParser().parse(f)

    with django.db.transaction.atomic():
        for dictionary in json_list:
            if dictionary['model'] == 'FileInstance':
                dictionary.pop('model')
                get_or_create_serialize_file_instance(dictionary)
            
            elif dictionary['model'] == 'BamFile':
                dictionary.pop('model')
                get_or_create_serialize_bam_file(dictionary)

