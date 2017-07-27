from django.conf.urls import url, include
from rest_framework import routers
from tantalus.api import views


router = routers.DefaultRouter()
router.register(r'sequence_file_resource', views.SequenceFileResourceViewSet)
router.register(r'indexed_reads', views.IndexedReadsViewSet)
router.register(r'sequence_lane', views.SequenceLaneViewSet)
router.register(r'fastq_file', views.PairedFastqFilesViewSet)
router.register(r'bam_file', views.BamFileViewSet)
router.register(r'server_storage', views.ServerStorageViewSet)
router.register(r'azure_blob_storage', views.AzureBlobStorageViewSet)
router.register(r'server_bam_file_instance', views.ServerBamFileInstanceViewSet)
router.register(r'server_fastq_file_instance', views.ServerPairedFastqFilesInstanceViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
]
