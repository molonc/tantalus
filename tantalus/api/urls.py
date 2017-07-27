from django.conf.urls import url, include
from rest_framework import routers
from tantalus.api import views


router = routers.DefaultRouter()
router.register(r'sequence_file_resource', views.SequenceDataFileViewSet)
router.register(r'indexed_reads', views.IndexedReadsViewSet)
router.register(r'sequence_lane', views.SequenceLaneViewSet)
router.register(r'fastq_file', views.PairedFastqFilesViewSet)
router.register(r'bam_file', views.BamFileViewSet)
router.register(r'azure_blob_storage', views.AzureBlobFileInstanceViewSet)
router.register(r'server_file_instance', views.ServerFileInstanceViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
]
