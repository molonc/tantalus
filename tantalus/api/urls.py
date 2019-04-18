from django.conf.urls import url, include
from rest_framework import routers, permissions
from tantalus.api import views
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework.authtoken import views as auth_views

router = routers.DefaultRouter()
router.register(r'analysis', views.AnalysisViewSet)
router.register(r'dna_library', views.DNALibraryViewSet)
router.register(r'file_instance', views.FileInstanceViewSet)
router.register(r'file_resource', views.FileResourceViewSet)
router.register(r'results', views.ResultsDatasetViewSet)
router.register(r'patients', views.PatientViewSet)
router.register(r'sample', views.SampleViewSet)
router.register(r'sequence_file_info', views.SequenceFileInfoViewSet)
router.register(r'sequencing_lane', views.SequencingLaneViewSet)
router.register(r'sequence_dataset', views.SequenceDatasetViewSet)
router.register(r'storage', views.StorageViewSet)
router.register(r'storage_server', views.ServerStorageViewSet)
router.register(r'storage_azure_blob', views.AzureBlobStorageViewSet)
router.register(r'tag', views.Tag)

# TODO: refactor sisyphus so it points to these
router.register(r'sequencedataset', views.SequenceDatasetViewSet)
router.register(r'resultsdataset', views.ResultsDatasetViewSet)

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
    url(r'^api-token-auth/', auth_views.obtain_auth_token),
    url(r'^auth/', include('rest_framework_social_oauth2.urls')),
    url(r'^', include(router.urls)),
]
