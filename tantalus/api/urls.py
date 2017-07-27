from django.conf.urls import url, include
from rest_framework import routers
from tantalus.api import views


urlpatterns = [
    url(r'sequence_file_resource/$', views.SequenceFileResourceList.as_view()),
]
