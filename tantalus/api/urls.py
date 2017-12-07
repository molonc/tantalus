from django.conf.urls import url, include
from rest_framework import routers
from tantalus.api import views


router = routers.DefaultRouter()
router.register(r'sample', views.SampleViewSet)
router.register(r'file_resource', views.FileResourceViewSet)
router.register(r'dna_library', views.DNALibraryViewSet)
router.register(r'dna_sequences', views.DNASequencesViewSet)
router.register(r'sequence_lane', views.SequenceLaneViewSet)
router.register(r'dataset/generic', views.AbstractDataSetViewSet)
router.register(r'dataset/single_end_fastq_file', views.SingleEndFastqFileViewSet)
router.register(r'dataset/paired_end_fastq_files', views.PairedEndFastqFilesViewSet)
router.register(r'dataset/bam_file', views.BamFileViewSet)
router.register(r'dataset/tag', views.DatasetsTag, base_name='tag')
router.register(r'storage/generic', views.StorageViewSet)
router.register(r'storage/server', views.ServerStorageViewSet)
router.register(r'storage/azure_blob', views.AzureBlobStorageViewSet)
router.register(r'file_instance', views.FileInstanceViewSet)
router.register(r'deployment', views.DeploymentViewSet)
router.register(r'file_transfer', views.FileTransferViewSet)
router.register(r'md5_check', views.MD5CheckViewSet)
router.register(r'queries/gsc_wgs_bams', views.QueryGscWgsBamsViewSet)
router.register(r'queries/gsc_dlp_paired_fastqs', views.QueryGscDlpPairedFastqsViewSet)
router.register(r'brc_import_fastqs', views.BRCImportFastqsViewSet)

# name to specify name space, all the views can be referred to as reverse('app_name:view_name')
# eg. reverse('api:deployment-list')
app_name='api'
urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^deployment/restart/(?P<pk>\d+)$', views.DeploymentRestart.as_view(), name='deployment-restart'),
]
