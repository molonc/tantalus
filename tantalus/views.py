from django.core.urlresolvers import reverse, reverse_lazy
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic.list import ListView
from django.views.generic import DetailView, FormView
from django.views.generic.base import TemplateView
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, render
from django_datatables_view.base_datatable_view import BaseDatatableView
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.template.defaulttags import register
from django.forms import ModelForm

import csv
import json
import os
from datetime import date
from sets import Set
import pandas as pd
from StringIO import StringIO
import xlsxwriter

from tantalus.utils import read_excel_sheets
from tantalus.settings import STATIC_ROOT
from misc.helpers import Render
import tantalus.models
import tantalus.tasks
import tantalus.forms


class ExternalIDSearch(TemplateView):

    search_template_name = "tantalus/external_id_search.html"
    result_template_name = "tantalus/external_id_results.html"

    def get_context_and_render(self, request, form):
        context = {
            'form': form,
        }
        return render(request, self.search_template_name, context)

    def render_results(self, request, sample_list, wrong_sample_list, multiple_sample_list):
        context = {
            'samples': sample_list,
            'multiple_samples': multiple_sample_list,
            'wrong_ids': wrong_sample_list,
        }
        return render(request, self.result_template_name, context)

    def get(self, request):
        form = tantalus.forms.ExternalIDSearcherForm()
        return self.get_context_and_render(request, form)

    def post(self, request):
        form = tantalus.forms.ExternalIDSearcherForm(request.POST)
        if form.is_valid():
            sample_list = []
            multiple_sample_list = []
            wrong_sample_list = []
            external_id_list = Set(form.cleaned_data['external_id_column'].encode('ascii','ignore').splitlines())

            for external_id in external_id_list:
                if(tantalus.models.Sample.objects.filter(external_sample_id=external_id).count() == 1):
                    sample_list.append(list(tantalus.models.Sample.objects.filter(external_sample_id=external_id))[0])
                elif(tantalus.models.Sample.objects.filter(external_sample_id=external_id).count() > 1):
                    for sample in tantalus.models.Sample.objects.filter(external_sample_id=external_id):
                        multiple_sample_list.append(sample)
                else:
                    wrong_sample_list.append(external_id)

            return self.render_results(request, sample_list, wrong_sample_list, multiple_sample_list)
        else:
            msg = "Failed to create search query. Please fix the errors below."
            messages.error(request, msg)
            return self.get_context_and_render(request, form)


@Render("tantalus/patient_list.html")
def patient_list(request):
    patients = tantalus.models.Patient.objects.all().order_by('patient_id')
    context = {
        'patients': patients
    }
    return context


class PatientDetail(DetailView):

    model = tantalus.models.Patient
    template_name = "tantalus/patient_detail.html"

    def get_context_data(self, **kwargs):
        # TODO: add other fields to the view?
        context = super(PatientDetail, self).get_context_data(**kwargs)

        sample_set = self.object.sample_set.all()
        sample_list = []
        sample_url = []

        for sample in sample_set:
            projects_list = []
            submission_list = []
            projects = sample.projects.all()
            for project in projects:
                projects_list.append(project.__unicode__())
            for submission in sample.submission_set.all():
                submission_list.append(submission.id)
            sample.projects_list = projects_list
            sample.submission_list = submission_list
            sample_list.append([sample.sample_id.encode('utf-8'), sample.get_absolute_url() + str(sample.id)])

        self.object.patient_id = self.object.patient_id.encode('utf-8')


        context['sample_list'] = sample_list
        context['samples'] = sample_set

        return context


@Render("tantalus/submission_list.html")
def submission_list(request):
    submissions = tantalus.models.Submission.objects.all().order_by('id')
    context = {
        'submissions': submissions
    }
    return context


class SubmissionDetail(DetailView):

    model = tantalus.models.Submission
    template_name = "tantalus/submission_detail.html"

    def get_context_data(self, **kwargs):
        # TODO: add other fields to the view?
        context = super(SubmissionDetail, self).get_context_data(**kwargs)
        sample_object = tantalus.models.Sample.objects.get(pk=self.object.sample_id)
        context['sample_url'] = sample_object.get_absolute_url() + str(self.object.sample.id)
        return context


@Render("tantalus/sample_list.html")
def sample_list(request):
    """
    List of samples.
    """

    samples = tantalus.models.Sample.objects.all().order_by('sample_id')

    context = {
        'samples': samples,
    }
    return context


class SampleDetail(DetailView):

    model = tantalus.models.Sample
    template_name = "tantalus/sample_detail.html"

    def get_context_data(self, **kwargs):
        # TODO: add other fields to the view?
        context = super(SampleDetail, self).get_context_data(**kwargs)

        submission_set = self.object.submission_set.all()
        project_set = self.object.projects.all()
        project_list = []

        for project in project_set:    
            project_list.append(project.__unicode__())

        try:
            context['patient_url'] = self.object.patient_id.get_absolute_url() + str(self.object.patient_id.id)
        except:
            context['patient_url'] = None
        context['project_list'] = project_list
        context['submission_set'] = submission_set
        return context


@Render("tantalus/result_list.html")
def result_list(request):
    results = tantalus.models.ResultsDataset.objects.all().order_by('id')

    context = {
        'results': results
    }
    return context


class ResultDetail(DetailView):
    model = tantalus.models.ResultsDataset
    template_name = "tantalus/result_detail.html"

    def get_context_data(self, **kwargs):
        # TODO: add other fields to the view?
        context = super(ResultDetail, self).get_context_data(**kwargs)
        sample_list = list(self.object.samples.all())

        for sample in sample_list:
            projects_list = []
            submission_list = []
            for project in sample.projects.all():
                projects_list.append(project.__unicode__())
            sample.projects_list = projects_list

            for submission in sample.submission_set.all():
                submission_list.append(submission.id)
            sample.submission_list = submission_list

        analysis = list(tantalus.models.Analysis.objects.filter(id=(self.object.analysis.id)))[0]
        context['input_datasets'] = analysis.input_datasets.all()
        context['file_resources'] = list(self.object.file_resources.all())
        context['samples'] = sample_list
        return context


@Render("tantalus/analysis_list.html")
def analysis_list(request):
    analyses = tantalus.models.Analysis.objects.all().order_by('id')

    context = {
        'analyses': analyses
    }
    return context


class AnalysisDetail(DetailView):
    model = tantalus.models.Analysis
    template_name = "tantalus/analysis_detail.html"

    def get_context_data(self, **kwargs):
        # TODO: add other fields to the view?
        context = super(AnalysisDetail, self).get_context_data(**kwargs)
        context['input_datasets'] = self.object.input_datasets.all()
        context['input_results'] = self.object.input_results.all()
        return context


class SimpleTaskListView(TemplateView):

    template_name = 'tantalus/simpletask_list.html'

    class Meta:
        abstract = True

    def get_context_data(self):
        context = {
            'tasks': self.task_model.objects.all(),
            'task_type': self.task_model.__name__,
        }
        return context


class FileTransferListView(SimpleTaskListView):

    task_model = tantalus.models.FileTransfer


class GscWgsBamQueryListView(SimpleTaskListView):

    task_model = tantalus.models.GscWgsBamQuery


class GscDlpPairedFastqQueryListView(SimpleTaskListView):

    task_model = tantalus.models.GscDlpPairedFastqQuery


class BRCFastqImportListView(SimpleTaskListView):

    task_model = tantalus.models.BRCFastqImport


class ImportDlpBamListView(SimpleTaskListView):

    task_model = tantalus.models.ImportDlpBam


def get_simple_task_log(simple_task, dir_name, stderr=False, raw=False, preview_size=1000):

    if stderr:
        kind = 'stderr'
    else:
        kind = 'stdout'

    simple_task_log_file_path = os.path.join(
        STATIC_ROOT,
        "logs/tasks/" + dir_name + "/{pk}/{kind}.txt".format(
            pk=simple_task.pk, kind=kind))

    if not os.path.exists(simple_task_log_file_path):
        return ['unable to open ' + simple_task_log_file_path]

    if raw:
        with open(simple_task_log_file_path, 'r') as log_file:
            return log_file.read()

    log = []
    with open(simple_task_log_file_path, 'r') as log_file:
        for i, line in enumerate(log_file):
            log.append(line)
            if preview_size is not None and len(log) >= preview_size:
                break

    return log


class SimpleTaskDetailView(TemplateView):

    template_name = 'tantalus/simpletask_detail.html'

    class Meta:
        abstract = True

    def get_context_data(self, **kwargs):
        simple_task = get_object_or_404(self.task_model, id=kwargs['pk'])
        try:
            stdout_page, stderr_page = self.request.GET.get('page', '1,1').split(',')
        except ValueError as e:
            stdout_page, stderr_page = 1, 1

        paginator_stdout = Paginator(get_simple_task_log(simple_task, self.task_model.task_name), 100)
        try:
            std = paginator_stdout.page(stdout_page)
        except PageNotAnInteger:
            std = paginator_stdout.page(1)
        except EmptyPage:
            std = paginator_stdout.page(paginator_stdout.num_pages)

        paginator_stderr = Paginator(get_simple_task_log(simple_task, self.task_model.task_name, stderr=True), 100)
        try:
            err = paginator_stderr.page(stderr_page)
        except PageNotAnInteger:
            err = paginator_stderr.page(1)
        except EmptyPage:
            err = paginator_stderr.page(paginator_stderr.num_pages)

        context = {
            'simple_task': simple_task,
            'std': std,
            'err': err,
            'task_type': self.task_model.__name__,
        }
        return context


class FileTransferDetailView(SimpleTaskDetailView):

    task_model = tantalus.models.FileTransfer


class GscWgsBamQueryDetailView(SimpleTaskDetailView):

    task_model = tantalus.models.GscWgsBamQuery


class GscDlpPairedFastqQueryDetailView(SimpleTaskDetailView):

    task_model = tantalus.models.GscDlpPairedFastqQuery


class BRCFastqImportDetailView(SimpleTaskDetailView):

    task_model = tantalus.models.BRCFastqImport


class ImportDlpBamDetailView(SimpleTaskDetailView):

    task_model = tantalus.models.ImportDlpBam


class SimpleTaskStdoutView(TemplateView):

    template_name = 'tantalus/simpletask_stdout.html'

    class Meta:
        abstract = True

    def get_context_data(self, **kwargs):
        simple_task = get_object_or_404(self.task_model, id=kwargs['pk'])

        context = {
            'simple_task_stdout': get_simple_task_log(simple_task, self.task_model.task_name, raw=True),
        }
        return context


class FileTransferStdoutView(SimpleTaskStdoutView):

    task_model = tantalus.models.FileTransfer


class GscWgsBamQueryStdoutView(SimpleTaskStdoutView):

    task_model = tantalus.models.GscWgsBamQuery


class GscDlpPairedFastqQueryStdoutView(SimpleTaskStdoutView):

    task_model = tantalus.models.GscDlpPairedFastqQuery


class BRCFastqImportStdoutView(SimpleTaskStdoutView):

    task_model = tantalus.models.BRCFastqImport


class ImportDlpBamStdoutView(SimpleTaskStdoutView):

    task_model = tantalus.models.ImportDlpBam


class SimpleTaskStderrView(TemplateView):

    template_name = 'tantalus/simpletask_stderr.html'

    class Meta:
        abstract = True

    def get_context_data(self, **kwargs):
        simple_task = get_object_or_404(self.task_model, id=kwargs['pk'])

        context = {
            'simple_task_stderr': get_simple_task_log(simple_task, self.task_model.task_name, stderr=True, raw=True),
        }
        return context


class FileTransferStderrView(SimpleTaskStderrView):

    task_model = tantalus.models.FileTransfer


class GscWgsBamQueryStderrView(SimpleTaskStderrView):

    task_model = tantalus.models.GscWgsBamQuery


class GscDlpPairedFastqQueryStderrView(SimpleTaskStderrView):

    task_model = tantalus.models.GscDlpPairedFastqQuery


class BRCFastqImportStderrView(SimpleTaskStderrView):

    task_model = tantalus.models.BRCFastqImport


class ImportDlpBamStderrView(SimpleTaskStderrView):

    task_model = tantalus.models.ImportDlpBam


@method_decorator(login_required, name='get')
class SimpleTaskCreateView(TemplateView):

    template_name = 'tantalus/simpletask_create.html'

    class Meta:
        abstract = True

    def get_context_and_render(self, request, form):
        context = {
            'form': form,
            'task_type': self.task_form.Meta.model.__name__,
        }
        return render(request, self.template_name, context)

    def get(self, request):
        form = self.task_form()
        return self.get_context_and_render(request, form)

    def post(self, request):
        form = self.task_form(request.POST)
        if form.is_valid():
            msg = "Successfully created the " + self.task_form.Meta.model.__name__ + "."
            messages.success(request, msg)
            instance = form.save()
            return HttpResponseRedirect(reverse(self.detail_url_name, kwargs={'pk':instance.id}))
        else:
            msg = "Failed to create the " + self.task_form.Meta.model.__name__ + ". Please fix the errors below."
            messages.error(request, msg)
        return self.get_context_and_render(request, form)


class FileTransferCreateView(SimpleTaskCreateView):

    task_form = tantalus.forms.FileTransferCreateForm
    detail_url_name = 'filetransfer-detail'

    def get(self, request):
        """Get the form.

        Differs from super method in that this allows initializing
        a tag name.
        """
        tag_query_param = request.GET.get('tag', None)

        if tag_query_param:
            form = self.task_form(initial={'tag_name': tag_query_param})
        else:
            form = self.task_form

        return self.get_context_and_render(request, form)


class GscWgsBamQueryCreateView(SimpleTaskCreateView):

    task_form = tantalus.forms.GscWgsBamQueryCreateForm
    detail_url_name = 'gscwgsbamquery-detail'


class GscDlpPairedFastqQueryCreateView(SimpleTaskCreateView):

    task_form = tantalus.forms.GscDlpPairedFastqQueryCreateForm
    detail_url_name = 'gscdlppairedfastqquery-detail'


class BRCFastqImportCreateView(SimpleTaskCreateView):

    task_form = tantalus.forms.BRCFastqImportCreateForm
    detail_url_name = 'brcfastqimport-detail'


class ImportDlpBamCreateView(SimpleTaskCreateView):

    task_form = tantalus.forms.ImportDlpBamCreateForm
    detail_url_name = 'importdlpbam-detail'


@method_decorator(login_required, name='get')
class SimpleTaskRestartView(View):

    class Meta:
        abstract = True

    def get(self, request, pk):
        simple_task = get_object_or_404(self.task_model, pk=pk)

        if simple_task.running:
            msg = "The " + self.task_model.__name__ + "is already running."
            messages.warning(request, msg)
            return HttpResponseRedirect(simple_task.get_absolute_url())

        simple_task.state = simple_task.task_name.replace('_', ' ') + ' queued'
        simple_task.save()
        task_id = self.task_type.apply_async(
            args=(simple_task.id,),
            queue=simple_task.get_queue_name())
        msg = "Successfully restarted the " + self.task_model.__name__ + " with id " + str(task_id) + " on " + simple_task.get_queue_name()
        messages.success(request, msg)
        return HttpResponseRedirect(reverse(self.detail_url_name,kwargs={'pk':simple_task.id}))


class FileTransferRestartView(SimpleTaskRestartView):

    # TODO: error for starting filetransfer that is running
    task_model = tantalus.models.FileTransfer
    task_type = tantalus.tasks.transfer_files_task
    detail_url_name = 'filetransfer-detail'

class GscWgsBamQueryRestartView(SimpleTaskRestartView):

    task_model = tantalus.models.GscWgsBamQuery
    task_type = tantalus.tasks.query_gsc_wgs_bams_task
    detail_url_name = 'gscwgsbamquery-detail'

class GscDlpPairedFastqQueryRestartView(SimpleTaskRestartView):

    task_model = tantalus.models.GscDlpPairedFastqQuery
    task_type = tantalus.tasks.query_gsc_dlp_paired_fastqs_task
    detail_url_name = 'gscdlppairedfastqquery-detail'


class BRCFastqImportRestartView(SimpleTaskRestartView):

    task_model = tantalus.models.BRCFastqImport
    task_type = tantalus.tasks.import_brc_fastqs_task
    detail_url_name = 'brcfastqimport-detail'


class ImportDlpBamRestartView(SimpleTaskRestartView):

    task_model = tantalus.models.ImportDlpBam
    task_type = tantalus.tasks.import_dlp_bams_task
    detail_url_name = 'importdlpbam-detail'


@method_decorator(login_required, name='get')
class SimpleTaskDeleteView(View):

    class Meta:
        abstract = True

    def get(self, request, pk):
        get_object_or_404(self.task_model, pk=pk).delete()
        msg = "Successfully deleted the " + self.task_model.__name__ + "."
        messages.success(request, msg)
        return HttpResponseRedirect(reverse(self.task_model.__name__.lower() + '-list'))


class FileTransferDeleteView(SimpleTaskDeleteView):

    task_model = tantalus.models.FileTransfer


class GscWgsBamQueryDeleteView(SimpleTaskDeleteView):

    task_model = tantalus.models.GscWgsBamQuery


class GscDlpPairedFastqQueryDeleteView(SimpleTaskDeleteView):

    task_model = tantalus.models.GscDlpPairedFastqQuery


class BRCFastqImportDeleteView(SimpleTaskDeleteView):

    task_model = tantalus.models.BRCFastqImport


class ImportDlpBamDeleteView(SimpleTaskDeleteView):

    task_model = tantalus.models.ImportDlpBam


@method_decorator(login_required, name='get')
class SimpleTaskStopView(View):

    class Meta:
        abstract = True

    def get(self, request, pk):
        simple_task = get_object_or_404(self.task_model, pk=pk)

        if simple_task.stopping == False:
            simple_task.stopping = True
            simple_task.save()
            msg = "Stopping the " + self.task_model.__name__ + "."
            messages.success(request, msg)
            return HttpResponseRedirect(simple_task.get_absolute_url())

        msg = "The " + self.task_model.__name__ + " is already stopping."
        messages.warning(request, msg)
        return HttpResponseRedirect(simple_task.get_absolute_url())


class FileTransferStopView(SimpleTaskStopView):

    task_model = tantalus.models.FileTransfer


class GscWgsBamQueryStopView(SimpleTaskStopView):

    task_model = tantalus.models.GscWgsBamQuery


class GscDlpPairedFastqQueryStopView(SimpleTaskStopView):

    task_model = tantalus.models.GscDlpPairedFastqQuery


class BRCFastqImportStopView(SimpleTaskStopView):

    task_model = tantalus.models.BRCFastqImport


class ImportDlpBamStopView(SimpleTaskStopView):

    task_model = tantalus.models.ImportDlpBam


@method_decorator(login_required, name='dispatch')
class PatientCreate(TemplateView):
    """
    tantalus.models.Patient create page.
    """

    template_name = "tantalus/patient_create.html"

    def get_context_and_render(self, request, form, pk=None):
        context = {
            'pk':pk,
            'form': form,
        }
        return render(request, self.template_name, context)

    def get(self, request, *args, **kwargs):
        form = tantalus.forms.PatientForm()
        return self.get_context_and_render(request, form)

    def post(self, request, *args, **kwargs):
        form = tantalus.forms.PatientForm(request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            msg = "Successfully created the tantalus.models.Patient."
            messages.success(request, msg)
            return HttpResponseRedirect(instance.get_absolute_url())
        else:
            msg = "Failed to create the Patient. Please fix the errors below."
            messages.error(request, msg)
            return self.get_context_and_render(request, form)


@method_decorator(login_required, name='dispatch')
class PatientEdit(TemplateView):

    template_name = "tantalus/patient_edit.html"

    def get_context_and_render(self, request, form, pk=None):
        context = {
            'pk':pk,
            'form': form,
        }
        return render(request, self.template_name, context)

    def get(self, request, *args, **kwargs):
        patient_pk = kwargs['pk']
        patient = tantalus.models.Patient.objects.get(id=patient_pk)
        form = tantalus.forms.PatientForm(instance=patient)
        return self.get_context_and_render(request, form, patient_pk)

    def post(self, request, *args, **kwargs):
        patient_pk = kwargs['pk']
        patient = tantalus.models.Patient.objects.get(id=patient_pk)
        form = tantalus.forms.PatientForm(request.POST, instance=patient)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            msg = "Successfully edited Patient {}.".format(patient.patient_id)
            messages.success(request, msg)
            return HttpResponseRedirect(instance.get_absolute_url())
        else:
            msg = "Failed to edit the Patient. Please fix the errors below."
            messages.error(request, msg)
            return self.get_context_and_render(request, form, patient_pk)


@method_decorator(login_required, name='dispatch')
class SubmissionCreate(TemplateView):
    """
    tantalus.models.Sample create page.
    """

    template_name = "tantalus/submission_create.html"

    def get_context_and_render(self, request, form, pk=None):
        context = {
            'pk':pk,
            'form': form,
        }
        return render(request, self.template_name, context)

    def get(self, request, *args, **kwargs):
        today = date.today().strftime('%B %d, %Y')
        form = tantalus.forms.SubmissionForm(initial={'submission_date': today, 'submitted_by': request.user})
        return self.get_context_and_render(request, form)

    def post(self, request, *args, **kwargs):
        form = tantalus.forms.SubmissionForm(request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            msg = "Successfully created the tantalus.models.Submission."
            messages.success(request, msg)
            return HttpResponseRedirect(instance.get_absolute_url())
        else:
            msg = "Failed to create the sample. Please fix the errors below."
            messages.error(request, msg)
            return self.get_context_and_render(request, form)


@method_decorator(login_required, name='dispatch')
class SpecificSubmissionCreate(TemplateView):
    """
    tantalus.models.Sample create page.
    """

    template_name = "tantalus/submission_create.html"

    def get_context_and_render(self, request, sample_pk, form, pk=None):
        context = {
            'pk':pk,
            'form': form,
            'sample_pk': sample_pk,
        }
        return render(request, self.template_name, context)

    def get(self, request, *args, **kwargs):
        today = date.today().strftime('%B %d, %Y')
        sample = get_object_or_404(tantalus.models.Sample,pk=kwargs['sample_pk'])
        print(sample.sample_id)
        form = tantalus.forms.SubmissionForm(initial={'submission_date': today, 'submitted_by': request.user, 'sample': sample})
        return self.get_context_and_render(request, kwargs['sample_pk'], form)

    def post(self, request, *args, **kwargs):
        form = tantalus.forms.SubmissionForm(request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            msg = "Successfully created the tantalus.models.Submission."
            messages.success(request, msg)
            return HttpResponseRedirect(instance.get_absolute_url())
        else:
            msg = "Failed to create the sample. Please fix the errors below."
            messages.error(request, msg)
            return self.get_context_and_render(request, form)


@method_decorator(login_required, name='dispatch')
class SampleCreate(TemplateView):
    """
    tantalus.models.Sample create page.
    """

    template_name = "tantalus/sample_create.html"

    def get_context_and_render(self, request, form, multi_form, pk=None):
        context = {
            'pk':pk,
            'form': form,
            'multi_form': multi_form,
        }
        return render(request, self.template_name, context)

    def get(self, request, *args, **kwargs):
        form = tantalus.forms.SampleForm()
        multi_form = tantalus.forms.UploadSampleForm()
        return self.get_context_and_render(request, form, multi_form)

    def post(self, request, *args, **kwargs):
        form = tantalus.forms.SampleForm(request.POST)
        multi_form = tantalus.forms.UploadSampleForm(request.POST, request.FILES)

        if form.is_valid():
            instance = form.save()
            msg = "Successfully created the tantalus.models.Sample."
            messages.success(request, msg)
            return HttpResponseRedirect(instance.get_absolute_url())
        elif multi_form.is_valid():
            samples_df = multi_form.get_sample_data()

            form_headers = samples_df.columns.tolist()

            external_patient_id_index = form_headers.index('External Patient ID')
            external_sample_id_index = form_headers.index('External Sample ID')
            patient_id_index = form_headers.index('Patient ID')
            suffix_index = form_headers.index('Suffix')            

            for idx, sample_row in samples_df.iterrows():
                if(pd.isnull(sample_row[patient_id_index])):
                    patient = tantalus.models.Patient.objects.get(external_patient_id=sample_row[external_patient_id_index])
                else:
                    patient = tantalus.models.Patient.objects.get(patient_id=sample_row[patient_id_index])
                if(sample_row[suffix_index] is None):
                    sample_id = patient.patient_id
                else:
                    sample_id = patient.patient_id + sample_row[suffix_index]
                external_sample_id = sample_row[external_sample_id_index]

                #Allow more fields in the future?
                sample_created, created = tantalus.models.Sample.objects.get_or_create(
                        sample_id=sample_id,
                        external_sample_id=external_sample_id,
                        patient_id=patient,
                    )
                if created:
                    sample_created.save()
            return HttpResponseRedirect(sample_created.get_absolute_url())
        else:
            msg = "Failed to create the sample. Please fix the errors below."
            messages.error(request, msg)
            return self.get_context_and_render(request, form, multi_form)


@method_decorator(login_required, name='dispatch')
class SpecificSampleCreate(TemplateView):
    """
    tantalus.models.Sample create page.
    """

    template_name = "tantalus/specific_sample_create.html"

    def get_context_and_render(self, request, form, patient_id, pk=None):
        context = {
            'pk':pk,
            'form': form,
            'patient_id': patient_id,
        }
        return render(request, self.template_name, context)

    def get(self, request, *args, **kwargs):
        patient_id = kwargs.get('patient_id').encode('utf-8')
        form = tantalus.forms.SampleForm(initial={'sample_id': patient_id, 'patient_id': patient_id})
        return self.get_context_and_render(request, form, patient_id)

    def post(self, request, *args, **kwargs):
        form = tantalus.forms.SampleForm(request.POST)

        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            msg = "Successfully created the tantalus.models.Sample."
            messages.success(request, msg)
            return HttpResponseRedirect(instance.get_absolute_url())
        else:
            msg = "Failed to create the sample. Please fix the errors below."
            messages.error(request, msg)
            patient_id = kwargs.get('patient_id').encode('utf-8')
            return self.get_context_and_render(request, form, patient_id)


@method_decorator(login_required, name='dispatch')
class SampleEdit(TemplateView):

    template_name = "tantalus/sample_edit.html"

    def get_context_and_render(self, request, form, pk=None):
        context = {
            'pk':pk,
            'form': form,
        }
        return render(request, self.template_name, context)

    def get(self, request, *args, **kwargs):
        sample_pk = kwargs['pk']
        sample = tantalus.models.Sample.objects.get(id=sample_pk)
        form = tantalus.forms.SampleForm(instance=sample)
        return self.get_context_and_render(request, form, sample_pk)

    def post(self, request, *args, **kwargs):
        sample_pk = kwargs['pk']
        sample = tantalus.models.Sample.objects.get(id=sample_pk)
        form = tantalus.forms.SampleForm(request.POST, instance=sample)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            msg = "Successfully edited Sample {}.".format(sample.sample_id)
            messages.success(request, msg)
            return HttpResponseRedirect(instance.get_absolute_url())
        else:
            msg = "Failed to edit the Sample. Please fix the errors below."
            messages.error(request, msg)
            return self.get_context_and_render(request, form, sample_pk)


def export_sample_create_template(request):
    header_dict = {
        'External Patient ID': [],
        'Patient ID': [],
        'External Sample ID': [],
        'Suffix': [],
    }
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="header-template.csv"'
    df = pd.DataFrame(header_dict)
    df.to_csv(response, index=False)
    return response


@Render("tantalus/tag_list.html")
def tag_list(request):
    """
    List of Tags.
    """
    tags = tantalus.models.Tag.objects.all().order_by('name')
    context = {
        'tags': tags,
    }
    return context


@method_decorator(login_required, name='dispatch')
class TagDelete(View):
    """
    tantalus.models.Tag delete page.
    """
    def get(self, request, pk):
        get_object_or_404(tantalus.models.Tag,pk=pk).delete()
        msg = "Successfully deleted tag"
        messages.success(request, msg)
        return HttpResponseRedirect(reverse('tag-list'))


class TagDetail(DetailView):
    model = tantalus.models.Tag
    template_name = "tantalus/tag_detail.html"

    def get_context_data(self, object):
        tag = get_object_or_404(tantalus.models.Tag, pk=object.id)
        sequence_datasets = tag.sequencedataset_set.all()
        results = tag.resultsdataset_set.all()
        context = {
            'tag': tag,
            'sequence_datasets': sequence_datasets,
            'results': results,
        }
        return context


@method_decorator(login_required, name='dispatch')
class TagDatasetDelete(View):
    """
    tantalus.models.Tag dataset delete page.
    """
    def get(self, request, pk,pk_2):
        dataset = get_object_or_404(tantalus.models.SequenceDataset,pk=pk)
        tag = get_object_or_404(tantalus.models.Tag,pk=pk_2)
        tag.sequencedataset_set.remove(dataset)
        msg = "Successfully removed datasest "
        messages.success(request, msg)
        return HttpResponseRedirect(reverse('tag-detail',kwargs={'pk':pk_2}))


class DatasetListJSON(BaseDatatableView):
    """
    Class used as AJAX data source through the ajax option in the abstractdataset_list template.
    This enables server-side processing of the data used in the javascript DataTables.
    """

    model = tantalus.models.SequenceDataset

    columns = ['id', 'dataset_type', 'sample_id', 'library_id','library_type', 'num_read_groups', 'num_total_read_groups', 'is_complete', 'tags', 'storages']

    # MUST be in the order of the columns
    order_columns = ['id', 'dataset_type', 'sample_id', 'library_id','library_type', 'num_read_groups', 'num_total_read_groups', 'is_complete', 'tags', 'storages']
    max_display_length = 100

    def get_context_data(self, *args, **kwargs):
        dataset_pks = self.request.session.get('dataset_search_results', None)
        if dataset_pks:
            kwargs['datasets'] = dataset_pks

        self.kwargs = kwargs
        return super(DatasetListJSON, self).get_context_data(*args, **kwargs)

    def get_initial_queryset(self):
        if 'datasets' in self.kwargs.keys():
            return tantalus.models.SequenceDataset.objects.filter(pk__in=self.kwargs['datasets'])
        return tantalus.models.SequenceDataset.objects.all()

    def render_column(self, row, column):
        if column == 'dataset_type':
            return row.dataset_type

        if column == 'sample_id':
            sample_link = (reverse('sample-detail', args=(row.sample.id,)))
            return "<a href=" + sample_link + ">" + row.sample.sample_id + "</a>"
        if column == 'library_id':
            return row.library.library_id

        if column == 'num_read_groups':
            return row.sequence_lanes.count()

        if column == 'tags':
            tags_string =  map(str, row.tags.all().values_list('name', flat=True))
            return tags_string

        if column == 'storages':
            return list(row.get_storage_names())

        if column == 'library_type':
            return row.library.library_type

        if column == 'num_total_read_groups':
            return row.get_num_total_sequencing_lanes()

        if column == 'is_complete':
            return row.get_is_complete()

        else:
            return super(DatasetListJSON, self).render_column(row, column)

    def filter_queryset(self, qs):

        """
        If search['value'] is provided then filter all searchable columns using istartswith.
        """

        if not self.pre_camel_case_notation:
            # get global search value
            search = self._querydict.get('search[value]', None)
            col_data = self.extract_datatables_column_data()
            q = Q()
            for col_no, col in enumerate(col_data):
                if search and col['searchable']:
                    # modified search queries for tags across related field manager
                    if col['name'] == 'tags':
                        q |= Q(tags__name__startswith=search)

                    elif col['name'] == 'sample_id':
                        q |= Q(sample__sample_id__startswith=search)

                    elif col['name'] == 'library_id':
                        q |= Q(library__library_id__startswith=search)

                    elif col['name'] == 'library_type':
                        q |= Q(library__library_type__startswith=search)

                    # standard search for simple . lookups across models
                    else:
                        # apply global search to all searchable columns
                        q |= Q(**{'{0}__startswith'.format(self.columns[col_no].replace('.', '__')): search})
                        # column specific filter
                        if col['search.value']:
                            qs = qs.filter(**{'{0}__startswith'.format(self.columns[col_no].replace('.', '__')): col['search.value']})

            qs = qs.filter(q).distinct()
        return qs


class DatasetList(ListView):

    model = tantalus.models.SequenceDataset
    template_name = "tantalus/abstractdataset_list.html"
    paginate_by = 100

    class Meta:
        ordering = ["id"]

    def get_context_data(self, **kwargs):

        # TODO: add other fields to the view?
        """
        Get context data, and pop session variables from search/tagging if they exist.
        """

        self.request.session.pop('dataset_search_results', None)
        self.request.session.pop('select_none_default', None)

        context = super(DatasetList, self).get_context_data(**kwargs)
        return context


class DatasetDetail(DetailView):

    model = tantalus.models.SequenceDataset
    template_name = "tantalus/abstractdataset_detail.html"

    def get_context_data(self, **kwargs):
        # TODO: add other fields to the view?
        context = super(DatasetDetail, self).get_context_data(**kwargs)
        storage_ids = self.object.get_storage_names()
        context['storages'] = storage_ids
        return context


@method_decorator(login_required, name='dispatch')
class DatasetDelete(View):
    """
    tantalus.models.SequenceDataset delete page.
    """
    def get(self, request, pk):
        dataset = get_object_or_404(tantalus.models.SequenceDataset, pk=pk)
        dataset.file_resources.all().delete()
        dataset.delete()
        msg = "Successfully removed datasest"
        messages.success(request, msg)
        return HttpResponseRedirect(reverse('dataset-list'))


class DatasetSearch(FormView):

    form_class = tantalus.forms.DatasetSearchForm
    success_url = reverse_lazy('dataset-tag')
    template_name = 'tantalus/abstractdataset_search_form.html'

    def post(self, request, *args, **kwargs):

        """
        Handles POST requests, instantiating a form instance with the passed POST variables and then checked for validity.
        """

        form = self.get_form()
        if form.is_valid():
            kwargs['kw_search_results'] = form.get_dataset_search_results()
            request.session['dataset_search_results'] = form.get_dataset_search_results()
            request.session.modified = True
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


@method_decorator(login_required, name='post')
class DatasetTag(FormView):
    form_class = tantalus.forms.DatasetTagForm
    template_name = 'tantalus/abstractdataset_tag_form.html'

    def get_context_data(self, **kwargs):

        """
        Insert the form into the context dict.
        Initialize queryset for tagging, and whether the default should have the whole queryset default to selected or not.
        """

        dataset_pks = self.request.session.get('dataset_search_results', None)
        if dataset_pks:
            datasets = tantalus.models.SequenceDataset.objects.filter(pk__in=dataset_pks)
            kwargs['datasets'] = datasets
            kwargs['dataset_pks'] = dataset_pks
        else:
            kwargs['datasets'] = tantalus.models.SequenceDataset.objects.all()
            kwargs['select_none_default'] = True

        if 'form' not in kwargs:
            kwargs['form'] = tantalus.forms.DatasetTagForm(datasets=dataset_pks)

        return super(DatasetTag, self).get_context_data(**kwargs)

    def get_form(self, form_class=None):

        """
        Returns an instance of the form to be used in this view.
        """

        if form_class is None:
            form_class = self.get_form_class()

        datasets = self.request.session.get('dataset_search_results', None)
        return form_class(datasets=datasets, **self.get_form_kwargs())

    def form_valid(self, form):
        form.add_dataset_tags()
        tag =  form.cleaned_data['tag_name']
        tag_id = tantalus.models.Tag.objects.get(name=tag)
        self.request.session.pop('dataset_search_results', None)
        self.request.session.pop('select_none_default', None)

        # Depending on which of the "tantalus.models.Tag" or "tantalus.models.Tag then transfer" buttons
        # was clicked to submit the form, take the appropriate action
        if self.request.POST.get('tag_and_transfer_button'):
            # Redirect to transfer
            return HttpResponseRedirect("%s?tag=%s" % (reverse('filetransfer-create'), tag))
        # Go to tantalus.models.Tag detail page
        return HttpResponseRedirect(reverse('tag-detail', kwargs={'pk': tag_id.id}))


@require_POST
def dataset_set_to_CSV(request):
    """A view to generate a CSV of datasets.

    Expects dataset_pks to be provided in the POST as a list of ints
    serialized as a string, each int of which corresponds to a dataset
    primary key.

    See https://docs.djangoproject.com/en/2.0/howto/outputting-csv/ for
    more info on outputting to CSV with Django.
    """
    # The http response, to which we'll write CSV rows to
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="datasets.csv"'

    # Set up an object to write CSVs to
    writer = csv.writer(response)

    # Functions to get dataset attributes. These need to return strings.
    def get_dataset_samples(instance):
        return instance.get_samples()

    def get_dataset_libraries(instance):
        return instance.get_libraries()

    def get_dataset_library_type(instance):
        return instance.get_library_type()

    def get_dataset_tags(instance):
        tags = instance.tags.all().values_list('name', flat=True)
        return ','.join([str(tag) for tag in tags])

    def get_dataset_storages(instance):
        storages = instance.get_storage_names()
        return ','.join(storages)

    def get_dataset_type(instance):
        return instance.get_dataset_type_name()

    def get_num_read(instance):
        return str(instance.get_num_total_sequencing_lanes())

    # Title and lambda function dictionary for dataset attributes used
    # for CSV header row. Each attribute has a title, used for the CSV
    # header row, and each attribute has a function, used getting the
    # value of the attribute, given a dataset instance.
    attribute_dict = {
            'pk': {'title': 'Dataset PK',
                   'function': lambda x: x.pk},
            'type': {'title': 'Type',
                     'function': get_dataset_type},
            'samples': {'title': 'Samples',
                        'function': get_dataset_samples},
            'libraries': {'title': 'Libraries',
                          'function': get_dataset_libraries},
            'library type': {'title': 'Library Type',
                             'function': get_dataset_library_type},
            'num read groups': {'title': 'Number of Read Groups',
                                'function': get_num_read},
            'tags': {'title': 'Tags',
                     'function': get_dataset_tags},
            'storages': {'title': 'Storages',
                         'function': get_dataset_storages},
            }

    # Dataset attributes to use. Choose from keys used in attribute_dict
    # above
    csv_attrs = ['pk',
                 'type',
                 'samples',
                 'libraries',
                 'library type',
                 'num read groups',
                 'tags',
                 'storages',]

    # Write the headers to the CSV file
    header_row = [attribute_dict[attr]['title'] for attr in csv_attrs]
    writer.writerow(header_row)

    # Get the datasets from the POST
    pks = sorted(json.loads(request.POST['dataset_pks']))
    datasets = tantalus.models.SequenceDataset.objects.filter(pk__in=pks)

    # Write the data from each dataset
    for dataset in datasets:
        # Get its attributes
        dataset_row = [attribute_dict[attr]['function'](dataset)
                                                        for attr in csv_attrs]

        # Write to CSV
        writer.writerow(dataset_row)

    return response


def get_storage_stats(storages=['all']):
    """A helper function to get data stats for all storages.

    Expects a list of storages as input, and outputs a dictionary of
    integers specifying the following:

    - num_bams: number of bam files in the storages
    - num_specs: number of spec files in the storages
    - num_bais: ...
    - num_fastqs: ...
    - num_active_file_transfers: ...
    - storage_size: size in bytes of files tracked on server
    """
    # Build the file instance set
    if 'all' in storages:
        file_resources = tantalus.models.FileResource.objects.all()
    else:
        file_resources = tantalus.models.FileResource.objects.filter(
            fileinstance__storage__name__in=storages)

    # Find info on number of files
    num_bams = file_resources.filter(
        file_type=tantalus.models.FileType.objects.get(name="BAM")).filter(
        ~Q(compression='SPEC')).count()
    num_specs = file_resources.filter(
        file_type=tantalus.models.FileType.objects.get(name="BAM")).filter(
        compression='SPEC').count()
    num_bais = file_resources.filter(
        file_type=tantalus.models.FileType.objects.get(name="BAI")).count()
    num_fastqs = file_resources.filter(
        file_type=tantalus.models.FileType.objects.get(name="FQ")).count()

    # Get the size of all storages
    storage_size = file_resources.aggregate(Sum('size'))
    storage_size = storage_size['size__sum']

    # Build the file transfer set
    if 'all' in storages:
        num_active_file_transfers = tantalus.models.FileTransfer.objects.filter(
            running=True).count()
    else:
        num_active_file_transfers = tantalus.models.FileTransfer.objects.filter(
            running=True).filter(
            Q(from_storage__name__in=storages)
            | Q(to_storage__name__in=storages)).count()

    return {'num_bams': num_bams,
            'num_specs': num_specs,
            'num_bais': num_bais,
            'num_fastqs': num_fastqs,
            'num_active_file_transfers': num_active_file_transfers,
            'storage_size': storage_size,
           }


def get_library_stats(filetype, storages_dict):
    """Get info on number of files in libraries.

    An assumption that this function makes is that all FASTQs come in
    the form of paired end FASTQs (cf. single end FASTQs). This
    assumption is currently true, and making it helps simplify the code
    a little.

    Args:
        filetype: A string which is either 'BAM' or 'FASTQ'.
        storages_dict: A dictionary where keys are storage names and
            values are a list of string of storage names. This framework
            lets us cluster several storages under a single name.
    Returns:
        A dictionary where the keys are the library types and the values
        are lists containing the name, file, and size count (under
        'name, 'file', and 'size') for each storage.
    """
    # Make sure the filetype is 'BAM' or 'FASTQ'
    assert filetype in ['BAM', 'FASTQ']

    # Get the list of library types that we'll get data for
    library_types = [x[0] for x in tantalus.models.DNALibrary.library_type_choices]

    # Results dictionary
    results = dict()

    # Go through each library
    for lib_type in library_types:
        # Make a list to store results in
        results[lib_type] = list()

        # Go through each storage
        for storage_name, storages in storages_dict.iteritems():
            # Get data for this storage and library. The distinct() at
            # the end of the queryset operations is necessary here, and
            # I'm not exactly sure why this is so, without it, filter
            # picks up a ton of duplicates. Very strange.
            matching_files = tantalus.models.FileResource.objects.filter(
                sequencedataset__library__library_type=lib_type).filter(
                fileinstance__storage__name__in=storages).distinct()

            if filetype == 'BAM':
                # Get all the matching BAM files
                matching_files = matching_files.filter(
                    file_type=tantalus.models.FileType.objects.get(name="BAM")
                )
            else:
                # Get all the matching FASTQ files
                matching_files = matching_files.filter(
                    file_type=tantalus.models.FileType.objects.get(name="FQ")
                )

            # Compute results - first the number of files- Add field skip_file_import to gscwgsbamquery
            number = matching_files.count()
            size = matching_files.aggregate(Sum('size'))
            size = size['size__sum']
            size = 0 if size is None else int(size)


            results[lib_type].append({
                'name': storage_name,
                'number': number,
                'size': size,
                })

    # Return the per-library results
    return results


class DataStatsView(TemplateView):
    """A view to show info on data statistics."""
    template_name = 'tantalus/data_stats.html'

    def get_context_data(self, **kwargs):
        """Get data info."""
        # Contains per-storage specific stats
        storage_stats = dict()

        # Go through local storages (i.e., non-cloud)
        for local_storage_name in ['gsc', 'shahlab', 'rocks']:
            # General stats
            storage_stats[local_storage_name] = (
                get_storage_stats([local_storage_name]))

        # Go through cloud storages.
        azure_storages = [x.name for x in tantalus.models.AzureBlobStorage.objects.all()]
        storage_stats['azure'] = get_storage_stats(azure_storages)

        # Get overall data stats over all storage locations
        storage_stats['all'] = get_storage_stats(['all'])

        # Contains per-library-type stats
        storages_dict = {'all': ['gsc', 'shahlab', 'rocks'] + azure_storages,
                         'gsc': ['gsc'],
                         'shahlab': ['shahlab'],
                         'rocks': ['rocks'],
                         'azure': azure_storages,
                        }
        bam_dict = get_library_stats('BAM', storages_dict)
        fastq_dict = get_library_stats('FASTQ', storages_dict)

        context = {
            'storage_stats': sorted(storage_stats.iteritems(),
                                            key=lambda (x, y): y['storage_size'],
                                            reverse=True),
            'locations_list': sorted(['all', 'azure', 'gsc', 'rocks', 'shahlab']),
            'bam_library_stats': sorted(bam_dict.iteritems()),
            'fastq_library_stats': sorted(fastq_dict.iteritems()),
            }
        return context


class HomeView(TemplateView):

    template_name = 'tantalus/index.html'

    def get_context_data(self, **kwargs):
        context = {
            'dataset_bam_count': tantalus.models.SequenceDataset.objects.filter(dataset_type='BAM').count(),
            'dataset_fastq_count': tantalus.models.SequenceDataset.objects.filter(dataset_type='FQ').count(),
            'patient_count': tantalus.models.Patient.objects.all().count(),
            'sample_count': tantalus.models.Sample.objects.all().count(),
            'submission_count': tantalus.models.Submission.objects.all().count(),
            'result_count': tantalus.models.ResultsDataset.objects.all().count(),
            'analysis_count': tantalus.models.Analysis.objects.all().count(),
            'tag_count': tantalus.models.Tag.objects.all().count(),
            'brc_fastq_import_count': tantalus.models.BRCFastqImport.objects.all().count(),
            'file_transfer_count': tantalus.models.FileTransfer.objects.all().count(),
            'gsc_dlp_paired_fastq_query_count': tantalus.models.GscDlpPairedFastqQuery.objects.all().count(),
            'gsc_wgs_bam_query_count': tantalus.models.GscWgsBamQuery.objects.all().count(),
            'import_dlp_bam_count': tantalus.models.ImportDlpBam.objects.all().count(),
        }
        return context
