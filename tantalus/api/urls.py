from django.conf.urls import url, include
from rest_framework import routers
from tantalus.api import views


router = routers.DefaultRouter()
router.register(r'sequence_file_resource', views.SequenceFileResourceViewSet)
router.register(r'indexed_reads', views.IndexedReadsViewSet)
router.register(r'sequence_lane', views.SequenceLaneViewSet)


urlpatterns = [
    url(r'^', include(router.urls)),
]
