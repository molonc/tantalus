from django.conf.urls import url, include
from rest_framework import routers
from tantalus.api import views


router = routers.DefaultRouter()
router.register(r'sample', views.SampleViewSet)
router.register(r'sequence_data_file', views.SequenceDataFileViewSet)
router.register(r'dna_library', views.DNALibraryViewSet)
router.register(r'dna_sequences', views.DNASequencesViewSet)
router.register(r'sequence_lane', views.SequenceLaneViewSet)
router.register(r'paired_fastq_files', views.PairedFastqFilesViewSet)
router.register(r'bam_file', views.BamFileViewSet)
router.register(r'azure_blob_storage', views.AzureBlobFileInstanceViewSet)
router.register(r'server_file_instance', views.ServerFileInstanceViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
]
