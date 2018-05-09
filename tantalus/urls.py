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
import tantalus.generictask_views
import account.views

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^api/', include('tantalus.api.urls')),
    url(r'^account/', include('account.urls')),
    url(r'^generictasktypes/$', tantalus.generictask_views.GenericTaskTypeListView.as_view(), name='generictasktype-list'),
    url(r'^generictasktypes/create$', tantalus.generictask_views.GenericTaskTypeCreateView.as_view(), name='generictasktype-create'),
    url(r'^generictasktypes/(?P<pk>\d+)$', tantalus.generictask_views.GenericTaskTypeDetailView.as_view(), name='generictasktype-detail'),
    url(r'^generictasktypes/delete/(?P<pk>\d+)$', tantalus.generictask_views.GenericTaskTypeDeleteView.as_view(), name='generictasktype-delete'),
    url(r'^generictaskinstances/$', tantalus.generictask_views.GenericTaskInstanceSubMenuView.as_view(), name='generictaskinstance-submenu'),
    url(r'^generictaskinstances/tasktype/(?P<task_type_pk>\d+)/instances$', tantalus.generictask_views.GenericTaskInstanceListView.as_view(), name='generictaskinstance-list'),
    url(r'^generictaskinstances/tasktype/(?P<task_type_pk>\d+)/instances/create$', tantalus.generictask_views.GenericTaskInstanceCreateView.as_view(), name='generictaskinstance-create'),
    url(r'^generictaskinstances/tasktype/(?P<task_type_pk>\d+)/instances/(?P<instance_pk>\d+)$', tantalus.generictask_views.GenericTaskInstanceDetailView.as_view(), name='generictaskinstance-detail'),
    url(r'^generictaskinstances/tasktype/(?P<task_type_pk>\d+)/instances/(?P<instance_pk>\d+)/logs/(?P<logfile>[-._a-zA-Z0-9]+)$', tantalus.generictask_views.GenericTaskInstanceLogView.as_view(), name='generictaskinstance-log'),
    url(r'^generictaskinstances/tasktype/(?P<task_type_pk>\d+)/instances/restart/(?P<instance_pk>\d+)$', tantalus.generictask_views.GenericTaskInstanceRestartView.as_view(), name='generictaskinstance-restart'),
    url(r'^generictaskinstances/tasktype/(?P<task_type_pk>\d+)/instances/stop/(?P<instance_pk>\d+)$', tantalus.generictask_views.GenericTaskInstanceStopView.as_view(), name='generictaskinstance-stop'),
    url(r'^generictaskinstances/tasktype/(?P<task_type_pk>\d+)/instances/delete/(?P<instance_pk>\d+)$', tantalus.generictask_views.GenericTaskInstanceDeleteView.as_view(), name='generictaskinstance-delete'),
    url(r'^filetransfers/$', tantalus.views.FileTransferListView.as_view(), name='filetransfer-list'),
    url(r'^filetransfers/create$', tantalus.views.FileTransferCreateView.as_view(), name='filetransfer-create'),
    url(r'^filetransfers/(?P<pk>\d+)$', tantalus.views.FileTransferDetailView.as_view(), name='filetransfer-detail'),
    url(r'^filetransfers/(?P<pk>\d+)/stdout$', tantalus.views.FileTransferStdoutView.as_view(), name='filetransfer-stdout'),
    url(r'^filetransfers/(?P<pk>\d+)/stderr$', tantalus.views.FileTransferStderrView.as_view(), name='filetransfer-stderr'),
    url(r'^filetransfers/restart/(?P<pk>\d+)$', tantalus.views.FileTransferRestartView.as_view(), name='filetransfer-restart'),
    url(r'^filetransfers/stop/(?P<pk>\d+)$', tantalus.views.FileTransferStopView.as_view(), name='filetransfer-stop'),
    url(r'^filetransfers/delete/(?P<pk>\d+)$', tantalus.views.FileTransferDeleteView.as_view(), name='filetransfer-delete'),
    url(r'^gscwgsbamqueries/$', tantalus.views.GscWgsBamQueryListView.as_view(), name='gscwgsbamquery-list'),
    url(r'^gscwgsbamqueries/create$', tantalus.views.GscWgsBamQueryCreateView.as_view(), name='gscwgsbamquery-create'),
    url(r'^gscwgsbamqueries/(?P<pk>\d+)$', tantalus.views.GscWgsBamQueryDetailView.as_view(), name='gscwgsbamquery-detail'),
    url(r'^gscwgsbamqueries/(?P<pk>\d+)/stdout$', tantalus.views.GscWgsBamQueryStdoutView.as_view(), name='gscwgsbamquery-stdout'),
    url(r'^gscwgsbamqueries/(?P<pk>\d+)/stderr$', tantalus.views.GscWgsBamQueryStderrView.as_view(), name='gscwgsbamquery-stderr'),
    url(r'^gscwgsbamqueries/restart/(?P<pk>\d+)$', tantalus.views.GscWgsBamQueryRestartView.as_view(), name='gscwgsbamquery-restart'),
    url(r'^gscwgsbamqueries/stop/(?P<pk>\d+)$', tantalus.views.GscWgsBamQueryStopView.as_view(), name='gscwgsbamquery-stop'),
    url(r'^gscwgsbamqueries/delete/(?P<pk>\d+)$', tantalus.views.GscWgsBamQueryDeleteView.as_view(), name='gscwgsbamquery-delete'),
    url(r'^gscdlppairedfastqqueries/$', tantalus.views.GscDlpPairedFastqQueryListView.as_view(), name='gscdlppairedfastqquery-list'),
    url(r'^gscdlppairedfastqqueries/create$', tantalus.views.GscDlpPairedFastqQueryCreateView.as_view(), name='gscdlppairedfastqquery-create'),
    url(r'^gscdlppairedfastqqueries/(?P<pk>\d+)$', tantalus.views.GscDlpPairedFastqQueryDetailView.as_view(), name='gscdlppairedfastqquery-detail'),
    url(r'^gscdlppairedfastqqueries/(?P<pk>\d+)/stdout$', tantalus.views.GscDlpPairedFastqQueryStdoutView.as_view(), name='gscdlppairedfastqquery-stdout'),
    url(r'^gscdlppairedfastqqueries/(?P<pk>\d+)/stderr$', tantalus.views.GscDlpPairedFastqQueryStderrView.as_view(), name='gscdlppairedfastqquery-stderr'),
    url(r'^gscdlppairedfastqqueries/restart/(?P<pk>\d+)$', tantalus.views.GscDlpPairedFastqQueryRestartView.as_view(), name='gscdlppairedfastqquery-restart'),
    url(r'^gscdlppairedfastqqueries/stop/(?P<pk>\d+)$', tantalus.views.GscDlpPairedFastqQueryStopView.as_view(), name='gscdlppairedfastqquery-stop'),
    url(r'^gscdlppairedfastqqueries/delete/(?P<pk>\d+)$', tantalus.views.GscDlpPairedFastqQueryDeleteView.as_view(), name='gscdlppairedfastqquery-delete'),
    url(r'^brcfastqimports/$', tantalus.views.BRCFastqImportListView.as_view(), name='brcfastqimport-list'),
    url(r'^brcfastqimports/create$', tantalus.views.BRCFastqImportCreateView.as_view(), name='brcfastqimport-create'),
    url(r'^brcfastqimports/(?P<pk>\d+)$', tantalus.views.BRCFastqImportDetailView.as_view(), name='brcfastqimport-detail'),
    url(r'^brcfastqimports/(?P<pk>\d+)/stdout$', tantalus.views.BRCFastqImportStdoutView.as_view(), name='brcfastqimport-stdout'),
    url(r'^brcfastqimports/(?P<pk>\d+)/stderr$', tantalus.views.BRCFastqImportStderrView.as_view(), name='brcfastqimport-stderr'),
    url(r'^brcfastqimports/restart/(?P<pk>\d+)$', tantalus.views.BRCFastqImportRestartView.as_view(), name='brcfastqimport-restart'),
    url(r'^brcfastqimports/stop/(?P<pk>\d+)$', tantalus.views.BRCFastqImportStopView.as_view(), name='brcfastqimport-stop'),
    url(r'^brcfastqimports/delete/(?P<pk>\d+)$', tantalus.views.BRCFastqImportDeleteView.as_view(), name='brcfastqimport-delete'),
    url(r'^samples/$', tantalus.views.sample_list, name='sample-list'),
    url(r'^samples/create$', tantalus.views.SampleCreate.as_view(), name='sample-add'),
    url(r'^samples/(?P<pk>\d+)$', tantalus.views.SampleDetail.as_view(), name='sample-detail'),
    url(r'^tags/$', tantalus.views.tag_list, name='tag-list'),
    url(r'^tags/detail/(?P<pk>\d+)$', tantalus.views.TagDetail.as_view(), name='tag-detail'),
    url(r'^tags/detail/(?P<pk>\d+)/delete/(?P<pk_2>[0-9]+)$', tantalus.views.TagDatasetDelete.as_view(), name='tag-dataset-delete'),
    url(r'^tags/delete/(?P<pk>\d+)$', tantalus.views.TagDelete.as_view(), name='tag-delete'),
    url(r'^datasets/$', tantalus.views.DatasetList.as_view(), name='dataset-list'),
    url(r'^datasets_json/$', tantalus.views.DatasetListJSON.as_view(), name='dataset-list-json'),
    url(r'^datasets/(?P<pk>\d+)$', tantalus.views.DatasetDetail.as_view(), name='dataset-detail'),
    url(r'^datasets/tag$', tantalus.views.DatasetTag.as_view(), name='dataset-tag'),
    url(r'^datasets/search$', tantalus.views.DatasetSearch.as_view(), name='dataset-search'),
    url(r'^$', tantalus.views.HomeView.as_view(), name='home'),
]
