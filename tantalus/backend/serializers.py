import django
import os
import sys
from django.utils.six import BytesIO
from rest_framework import serializers
from rest_framework.parsers import JSONParser

from tantalus.utils import start_md5_checks
import tantalus.models


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
        model = tantalus.models.Sample
        fields = ('sample_id', )


def get_or_create_serialize_sample(data):
    sample_serializer = SampleSerializer(data=data)
    sample_serializer.is_valid(raise_exception=True)
    return sample_serializer.instance.id


class DNALibrarySerializer(GetCreateModelSerializer):
    class Meta:
        model = tantalus.models.DNALibrary
        fields = ('library_id', 'library_type', 'index_format')


def get_or_create_serialize_dna_library(data):
    dna_library_serializer = DNALibrarySerializer(data=data)
    dna_library_serializer.is_valid(raise_exception=True)
    return dna_library_serializer.instance.id


class FileResourceSerializer(GetCreateModelSerializer):
    class Meta:
        model = tantalus.models.FileResource
        fields = ('size', 'created', 'file_type', 'read_end', 'compression', 'filename')


def get_or_create_serialize_file_resource(data):
    file_resource_serializer = FileResourceSerializer(data=data)
    file_resource_serializer.is_valid(raise_exception=True)
    return file_resource_serializer.instance.id


class SequencingLaneSerializer(GetCreateModelSerializer):
    class Meta:
        model = tantalus.models.SequencingLane
        fields = ('flowcell_id', 'lane_number', 'dna_library_id', 'sequencing_centre', 'sequencing_instrument', 'read_type')


def get_or_create_serialize_sequence_lane(data):
    data['dna_library_id'] = tantalus.models.DNALibrary.objects.get(**data.pop('dna_library')).id

    sequence_lane_serializer = SequencingLaneSerializer(data=data)
    sequence_lane_serializer.is_valid(raise_exception=True)
    return sequence_lane_serializer.instance.id


class FileInstanceSerializer(GetCreateModelSerializer):
    class Meta:
        model = tantalus.models.FileInstance
        fields = ('storage_id', 'file_resource_id', 'filename_override')


def get_or_create_serialize_file_instance(data):
    data['storage_id'] = tantalus.models.Storage.objects.get(**data.pop('storage')).id
    data['file_resource_id'] = get_or_create_serialize_file_resource(data.pop('file_resource'))

    file_instance_serializer = FileInstanceSerializer(data=data)
    file_instance_serializer.is_valid(raise_exception=True)
    return file_instance_serializer.instance.id


class SequenceDatasetSerializer(GetCreateModelSerializer):
    class Meta:
        model = tantalus.models.SequenceDataset
        fields = ('name', 'dataset_type', 'sample', 'library', 'file_resources', 'sequence_lanes')
        

def get_or_create_serialize_sequence_dataset(data):
    data['sample_id'] = get_or_create_serialize_sample(data.pop('sample'))
    data['library_id'] = get_or_create_serialize_dna_library(data.pop('library'))

    file_resources = data.pop('file_resources')
    sequence_lanes = data.pop('sequence_lanes')

    sequence_dataset_serializer = SequenceDatasetSerializer(data=data)
    sequence_dataset_serializer.is_valid(raise_exception=True)

    for file_resource in file_resources:
        sequence_dataset_serializer.instance.file_resources.add(get_or_create_serialize_file_resource(file_resource))

    for sequence_lane in sequence_lanes:
        sequence_dataset_serializer.instance.sequence_lanes.add(get_or_create_serialize_sequence_lane(sequence_lane))

    return sequence_dataset_serializer.instance


def read_models(json_data_filename, tag_name=None):
    with open(json_data_filename) as f:
        json_list = JSONParser().parse(f)

    with django.db.transaction.atomic():
        tag = None
        if tag_name:
            tag = tantalus.models.Tag.objects.get_or_create(name=tag_name)
        for dictionary in json_list:
            if dictionary['model'] == 'FileInstance':
                dictionary.pop('model')
                get_or_create_serialize_file_instance(dictionary)

            elif dictionary['model'] == 'SequenceDataset':
                dictionary.pop('model')
                dataset = get_or_create_serialize_sequence_dataset(dictionary)
                if tag:
                    dataset.tags.add(tag)

            elif dictionary['model'] == 'SequenceLane':
                dictionary.pop('model')
                get_or_create_serialize_sequence_lane(dictionary)

            else:
                raise ValueError('model type {} not supported'.format(dictionary['model']))


