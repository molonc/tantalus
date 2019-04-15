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
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView
from django.conf import settings
from django.urls import path
import tantalus.views
import account.views
from rest_framework.authtoken import views

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^api/', include('tantalus.api.urls')),
    url(r'^account/', include('account.urls')),
    url(r'^samples/$', tantalus.views.sample_list, name='sample-list'),
    url(r'^samples/create$', tantalus.views.SampleCreate.as_view(), name='sample-add'),
    url(r'^samples/create/(?P<patient_id>.{1,20})$', tantalus.views.SpecificSampleCreate.as_view(), name='specific-sample-add'),
    url(r'^samples/confirm-samples-create$', tantalus.views.ConfirmSamplesCreate.as_view(), name='confirm-samples-create'),
    url(r'^samples/(?P<pk>\d+)$', tantalus.views.SampleDetail.as_view(), name='sample-detail'),
    url(r'^samples/edit/(?P<pk>\d+)$', tantalus.views.SampleEdit.as_view(), name='sample-edit'),
    url(r'^export-sample-create-template/$', tantalus.views.export_sample_create_template, name='export-sample-create-template'),
    url(r'^tags/$', tantalus.views.tag_list, name='tag-list'),
    url(r'^tags/detail/(?P<pk>\d+)$', tantalus.views.TagDetail.as_view(), name='tag-detail'),
    url(r'^tags/detail/(?P<pk>\d+)/deletedataset/(?P<pk_2>[0-9]+)$', tantalus.views.TagDatasetDelete.as_view(), name='tag-dataset-delete'),
    url(r'^tags/detail/(?P<pk>\d+)/deleteresults/(?P<pk_2>[0-9]+)$', tantalus.views.TagResultsDelete.as_view(), name='tag-results-delete'),
    url(r'^tags/delete/(?P<pk>\d+)$', tantalus.views.TagDelete.as_view(), name='tag-delete'),
    url(r'^datasets/$', tantalus.views.DatasetList.as_view(), name='dataset-list'),
    url(r'^datasets/(?P<pk>\d+)$', tantalus.views.DatasetDetail.as_view(), name='dataset-detail'),
    url(r'^datasets/tag$', tantalus.views.DatasetTag.as_view(), name='dataset-tag'),
    url(r'^datasets/create-analysis$', tantalus.views.dataset_analysis_ajax, name='dataset-analysis-ajax'),
    url(r'^datasets/tag/csv$', tantalus.views.dataset_set_to_CSV, name='dataset-tag-csv'),
    url(r'^datasets/search$', tantalus.views.DatasetSearch.as_view(), name='dataset-search'),
    url(r'^datasets/delete/(?P<pk>\d+)$', tantalus.views.DatasetDelete.as_view(), name='dataset-delete'),
    url(r'^data_stats$', tantalus.views.DataStatsView.as_view(), name='data-stats'),
    url(r'^patients/$', tantalus.views.patient_list, name='patient-list'),
    url(r'^patients/(?P<pk>\d+)$', tantalus.views.PatientDetail.as_view(), name='patient-detail'),
    url(r'^patients/edit/(?P<pk>\d+)$', tantalus.views.PatientEdit.as_view(), name='patient-edit'),
    url(r'^patients/create$', tantalus.views.PatientCreate.as_view(), name='patient-add'),
    url(r'^patients/confirm-patient-edit-from-create$', tantalus.views.ConfirmPatientEditFromCreate.as_view(), name='confirm-patient-edit-from-create'),
    url(r'^export-patient-create-template/$', tantalus.views.export_patient_create_template, name='export-patient-create-template'),
    url(r'^submissions/$', tantalus.views.submission_list, name='submissions-list'),
    url(r'^submissions/(?P<pk>\d+)$', tantalus.views.SubmissionDetail.as_view(), name='submission-detail'),
    url(r'^submissions/create$', tantalus.views.SubmissionCreate.as_view(), name='submission-add'),
    url(r'^submissions/create/(?P<sample_pk>.{1,20})$', tantalus.views.SpecificSubmissionCreate.as_view(), name='specific-submission-add'),
    url(r'^results/$', tantalus.views.result_list, name='result-list'),
    url(r'^results/(?P<pk>\d+)$', tantalus.views.ResultDetail.as_view(), name='result-detail'),
    url(r'^analyses/create$', tantalus.views.AnalysisCreate.as_view(), name='analysis-add'),
    url(r'^analyses/create/datasets$', tantalus.views.AnalysisCreate.as_view(), name='analysis-add-dataset'),
    url(r'^analyses/$', tantalus.views.analysis_list, name='analysis-list'),
    url(r'^analyses/(?P<pk>\d+)$', tantalus.views.AnalysisDetail.as_view(), name='analysis-detail'),
    url(r'^analyses/edit/(?P<pk>\d+)$', tantalus.views.AnalysisEdit.as_view(), name='analysis-edit'),
    url(r'^externalidsearch/$', tantalus.views.ExternalIDSearch.as_view(), name='external-id-search'),
    url(r'^export-external-id-results/$', tantalus.views.export_external_id_results, name='export-external-id-results'),
    url(r'^$', tantalus.views.HomeView.as_view(), name='home'),
    url(r'^associateazure', tantalus.views.AssociateAzureView.as_view(), name='associate-azure'),
    url(r'^auth/', include('rest_framework_social_oauth2.urls')),
    url('', include('django.contrib.auth.urls')),
    url('', include('social_django.urls', namespace='social')),
    url('logout/', auth_views.LogoutView.as_view(), {'next_page': settings.LOGOUT_REDIRECT_URL}, name='logout'),
    url(r'^json/datasets/$', tantalus.views.DatasetListJSON.as_view(), name='dataset-list-json'),
    url(r'^json/fileresources/$', tantalus.views.FileResourceJSON.as_view(), name='fileresources-list-json'),
    url(r'^api-token-auth/', views.obtain_auth_token)
]
