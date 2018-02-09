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
    url(r'^filetransfers/$', tantalus.views.FileTransferListView.as_view(), name='filetransfer-list'),
    url(r'^filetransfers/create$', tantalus.views.FileTransferCreateView.as_view(), name='filetransfer-create'),
    url(r'^filetransfers/(?P<pk>\d+)$', tantalus.views.FileTransferDetailView.as_view(), name='filetransfer-detail'),
    url(r'^filetransfers/(?P<pk>\d+)/detail$', tantalus.views.FileTransferStdoutView.as_view(), name='filetransfer-stdout'),
    url(r'^filetransfers/(?P<pk>\d+)/error$', tantalus.views.FileTransferStderrView.as_view(), name='filetransfer-stderr'),
    url(r'^filetransfers/start/(?P<pk>\d+)$', tantalus.views.FileTransferStartView.as_view(), name='filetransfer-start'),
    url(r'^gscwgsbamqueries/$', tantalus.views.GscWgsBamQueryListView.as_view(), name='gscwgsbamquery-list'),
    url(r'^gscwgsbamqueries/create$', tantalus.views.GscWgsBamQueryCreateView.as_view(), name='gscwgsbamquery-create'),
    url(r'^gscwgsbamqueries/(?P<pk>\d+)$', tantalus.views.GscWgsBamQueryDetailView.as_view(), name='gscwgsbamquery-detail'),
    url(r'^gscwgsbamqueries/(?P<pk>\d+)/detail$', tantalus.views.GscWgsBamQueryStdoutView.as_view(), name='gscwgsbamquery-stdout'),
    url(r'^gscwgsbamqueries/(?P<pk>\d+)/error$', tantalus.views.GscWgsBamQueryStderrView.as_view(), name='gscwgsbamquery-stderr'),
    url(r'^gscwgsbamqueries/start/(?P<pk>\d+)$', tantalus.views.GscWgsBamQueryStartView.as_view(), name='gscwgsbamquery-start'),
    url(r'^gscdlppairedfastqqueries/$', tantalus.views.GscDlpPairedFastqQueryListView.as_view(), name='gscdlppairedfastqquery-list'),
    url(r'^gscdlppairedfastqqueries/create$', tantalus.views.GscDlpPairedFastqQueryCreateView.as_view(), name='gscdlppairedfastqquery-create'),
    url(r'^gscdlppairedfastqqueries/(?P<pk>\d+)$', tantalus.views.GscDlpPairedFastqQueryDetailView.as_view(), name='gscdlppairedfastqquery-detail'),
    url(r'^gscdlppairedfastqqueries/(?P<pk>\d+)/detail$', tantalus.views.GscDlpPairedFastqQueryStdoutView.as_view(), name='gscdlppairedfastqquery-stdout'),
    url(r'^gscdlppairedfastqqueries/(?P<pk>\d+)/error$', tantalus.views.GscDlpPairedFastqQueryStderrView.as_view(), name='gscdlppairedfastqquery-stderr'),
    url(r'^gscdlppairedfastqqueries/start/(?P<pk>\d+)$', tantalus.views.GscDlpPairedFastqQueryStartView.as_view(), name='gscdlppairedfastqquery-start'),
    url(r'^brcfastqimports/$', tantalus.views.BRCFastqImportListView.as_view(), name='brcfastqimport-list'),
    url(r'^brcfastqimports/create$', tantalus.views.BRCFastqImportCreateView.as_view(), name='brcfastqimport-create'),
    url(r'^brcfastqimports/(?P<pk>\d+)$', tantalus.views.BRCFastqImportDetailView.as_view(), name='brcfastqimport-detail'),
    url(r'^brcfastqimports/(?P<pk>\d+)/detail$', tantalus.views.BRCFastqImportStdoutView.as_view(), name='brcfastqimport-stdout'),
    url(r'^brcfastqimports/(?P<pk>\d+)/error$', tantalus.views.BRCFastqImportStderrView.as_view(), name='brcfastqimport-stderr'),
    url(r'^brcfastqimports/start/(?P<pk>\d+)$', tantalus.views.BRCFastqImportStartView.as_view(), name='brcfastqimport-start'),
    url(r'^samples/$', tantalus.views.sample_list, name='sample-list'),
    url(r'^samples/create$', tantalus.views.SampleCreate.as_view(), name='sample-add'),
    url(r'^samples/(?P<pk>\d+)$', tantalus.views.SampleDetail.as_view(), name='sample-detail'),
    url(r'^datasets/$', tantalus.views.DatasetList.as_view(), name='dataset-list'),
    url(r'^datasets_json/$', tantalus.views.DatasetListJSON.as_view(), name='dataset-list-json'),
    url(r'^datasets/(?P<pk>\d+)$', tantalus.views.DatasetDetail.as_view(), name='dataset-detail'),
    url(r'^datasets/tag$', tantalus.views.DatasetTag.as_view(), name='dataset-tag'),
    url(r'^datasets/search$', tantalus.views.DatasetSearch.as_view(), name='dataset-search'),
    url(r'^$', tantalus.views.HomeView.as_view(), name='home')
]
