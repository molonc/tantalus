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

