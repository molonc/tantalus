from rest_framework import viewsets
from rest_framework import generics
from tantalus.models import SequenceFileResource
from tantalus.api.serializers import SequenceFileResourceSerializer


# generics.ListCreateAPIView
# generics.RetrieveUpdateDestroyAPIView

class SequenceFileResourceList(generics.ListCreateAPIView):
    queryset = SequenceFileResource.objects.all()
    serializer_class = SequenceFileResourceSerializer
