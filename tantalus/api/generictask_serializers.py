"""Serializers relating to the GenericTask models."""

from rest_framework import serializers
from tantalus.generictask_models import GenericTaskType, GenericTaskInstance


class GenericTaskTypeSerializer(serializers.ModelSerializer):
    """A serializer for a generic task type."""
    class Meta:
        model = GenericTaskType
        fields = '__all__'

class GenericTaskInstanceSerializer(serializers.ModelSerializer):
    """A serializer for a generic task instance."""
    # Job feedback fields
    running = serializers.BooleanField(read_only=True)
    finished = serializers.BooleanField(read_only=True)
    success = serializers.BooleanField(read_only=True)
    stopping = serializers.BooleanField(read_only=True)
    state = serializers.CharField(read_only=True)

    class Meta:
        model = GenericTaskInstance
        fields = '__all__'
