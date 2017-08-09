from django.conf.urls import url, include
from rest_framework import routers
from tantalus.api import views


router = routers.DefaultRouter()
router.register(r'sample', views.SampleViewSet)
router.register(r'sequence_data_file', views.SequenceDataFileViewSet)
router.register(r'dna_library', views.DNALibraryViewSet)
router.register(r'dna_sequences', views.DNASequencesViewSet)
router.register(r'sequence_lane', views.SequenceLaneViewSet)
router.register(r'sequence_dataset', views.SequenceDatasetViewSet)
router.register(r'single_end_fastq_file', views.SingleEndFastqFileViewSet)
router.register(r'paired_end_fastq_files', views.PairedEndFastqFilesViewSet)
router.register(r'bam_file', views.BamFileViewSet)
router.register(r'storage', views.StorageViewSet)
router.register(r'storage/server', views.ServerStorageViewSet)
router.register(r'storage/azure_blob', views.AzureBlobStorageViewSet)
router.register(r'file_instance', views.FileInstanceViewSet)
router.register(r'deployment', views.DeploymentViewSet)
router.register(r'file_transfer', views.FileTransferViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
]
