from rest_framework import serializers
import tantalus.models

class SequenceFileResourceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = tantalus.models.SequenceFileResource
        fields = '__all__'
