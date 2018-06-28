from django.conf.urls import url, include
from rest_framework import routers, permissions
from tantalus.api import views
from tantalus.api import generictask_api_views
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

router = routers.DefaultRouter()
router.register(r'sample', views.SampleViewSet)
router.register(r'file_resource', views.FileResourceViewSet)
router.register(r'dna_library', views.DNALibraryViewSet)
router.register(r'read_group', views.ReadGroupViewSet)
router.register(r'sequence_lane', views.SequenceLaneViewSet)
router.register(r'dataset/generic', views.AbstractDataSetViewSet)
router.register(r'dataset/single_end_fastq_file', views.SingleEndFastqFileViewSet)
router.register(r'dataset/paired_end_fastq_files', views.PairedEndFastqFilesViewSet)
router.register(r'dataset/bam_file', views.BamFileViewSet)
router.register(r'dataset/add', views.AddDataView, base_name='add')
router.register(r'dataset/tag', views.DatasetsTag, base_name='tag')
router.register(r'dataset/bcl_folder', views.BCLFolderViewSet)
router.register(r'storage/generic', views.StorageViewSet)
router.register(r'storage/server', views.ServerStorageViewSet)
router.register(r'storage/azure_blob', views.AzureBlobStorageViewSet)
router.register(r'file_instance', views.FileInstanceViewSet)
router.register(r'file_transfer', views.FileTransferViewSet)
router.register(r'md5_check', views.MD5CheckViewSet)
router.register(r'queries/gsc_wgs_bams', views.QueryGscWgsBamsViewSet)
router.register(r'queries/gsc_dlp_paired_fastqs', views.QueryGscDlpPairedFastqsViewSet)
router.register(r'brc_import_fastqs', views.BRCImportFastqsViewSet)
router.register(r'import_dlp_bam', views.ImportDlpBamViewSet)
router.register(r'generic_task_types', generictask_api_views.GenericTaskTypeViewSet)
router.register(r'generic_task_instances', generictask_api_views.GenericTaskInstanceViewSet)

# Schema for Swagger API
schema_view = get_schema_view(
    openapi.Info(
        title="Tantalus API",
        default_version='v1',),
   validators=['flex', 'ssv'],
   public=True,
   permission_classes=(permissions.IsAuthenticatedOrReadOnly,),
)

# name to specify name space, all the views can be referred to as reverse('app_name:view_name')
# eg. reverse('api:filetransfer-list')
app_name='api'
urlpatterns = [
    url(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=None), name='schema-json'),
    url(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=None), name='schema-swagger-ui'),
    url(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=None), name='schema-redoc'),
    url(r'^', include(router.urls)),
    url(r'^file_transfer/restart/(?P<pk>\d+)$', views.FileTransferRestart.as_view(), name='filetransfer-restart'),
]
