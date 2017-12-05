"""tantalus URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""

from django.conf.urls import url, include
from django.contrib import admin
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView
import tantalus.views
import account.views

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^api/', include('tantalus.api.urls')),
    url(r'^account/', include('account.urls')),
    url(r'^search/', tantalus.views.search_view, name='search'),
    url(r'^transfers$', tantalus.views.FileTransferView.as_view(), name='transfer-list'),
    url(r'^deployments/$', tantalus.views.DeploymentView.as_view(), name='deployment-list'),
    url(r'^deployments/create$', tantalus.views.DeploymentCreateView.as_view(), name='deployment-create'),
    url(r'^deployments/(?P<pk>\d+)$', tantalus.views.DeploymentDetailView.as_view(), name='deployment-detail'),
    url(r'^deployments/start/(?P<pk>\d+)$', tantalus.views.start_deployment, name='deployment-start'),
    url(r'^samples/$', tantalus.views.sample_list, name='sample-list'),
    url(r'^samples/create$', tantalus.views.SampleCreate.as_view(), name='sample-add'),
    url(r'^datasets/$', tantalus.views.DatasetList.as_view(), name='dataset-list'),
    url(r'^datasets_json/$', tantalus.views.DatasetListJSON.as_view(), name='dataset-list-json'),
    url(r'^datasets/(?P<pk>\d+)$', tantalus.views.DatasetDetail.as_view(), name='dataset-detail'),
    url(r'^datasets/tag$', tantalus.views.DatasetTag.as_view(), name='dataset-tag'),
    url(r'^datasets/search$', tantalus.views.DatasetSearch.as_view(), name='dataset-search'),
    url(r'^$', tantalus.views.HomeView.as_view(), name='home')
]
