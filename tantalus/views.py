from django.core.urlresolvers import reverse, reverse_lazy
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic.list import ListView
from django.views.generic import DetailView, FormView
from django.views.generic.base import TemplateView
from django.db import transaction
from django.shortcuts import get_object_or_404, render
from django_datatables_view.base_datatable_view import BaseDatatableView
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

import os

from tantalus.models import FileTransfer, FileResource, Sample, AbstractDataSet, Storage, GscWgsBamQuery, GscDlpPairedFastqQuery, BRCFastqImport, Tag
from tantalus.generictask_models import GenericTaskType, GenericTaskInstance
from tantalus.utils import read_excel_sheets
from tantalus.settings import STATIC_ROOT
from misc.helpers import Render
from .forms import SampleForm, MultipleSamplesForm, DatasetSearchForm, DatasetTagForm, FileTransferCreateForm, GscWgsBamQueryCreateForm, GscDlpPairedFastqQueryCreateForm, BRCFastqImportCreateForm
import tantalus.tasks


@Render("tantalus/sample_list.html")
def sample_list(request):
    
    """
    List of samples.
    """
    
    samples = Sample.objects.all().order_by('sample_id')
    
    context = {
        'samples': samples,
    }
    return context


class SampleDetail(DetailView):

    model = Sample
    template_name = "tantalus/sample_detail.html"

    def get_context_data(self, object):
        instance = get_object_or_404(Sample, pk=object.id)
        
        context = {
            'form': SampleForm(instance=instance),
        }
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
    
    task_model = FileTransfer


class GscWgsBamQueryListView(SimpleTaskListView):
    
    task_model = GscWgsBamQuery


class GscDlpPairedFastqQueryListView(SimpleTaskListView):
    
    task_model = GscDlpPairedFastqQuery


class BRCFastqImportListView(SimpleTaskListView):
    
    task_model = BRCFastqImport


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

    task_model = FileTransfer


class GscWgsBamQueryDetailView(SimpleTaskDetailView):
    
    task_model = GscWgsBamQuery


class GscDlpPairedFastqQueryDetailView(SimpleTaskDetailView):
    
    task_model = GscDlpPairedFastqQuery


class BRCFastqImportDetailView(SimpleTaskDetailView):
    
    task_model = BRCFastqImport


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

    task_model = FileTransfer


class GscWgsBamQueryStdoutView(SimpleTaskStdoutView):
    
    task_model = GscWgsBamQuery


class GscDlpPairedFastqQueryStdoutView(SimpleTaskStdoutView):
    
    task_model = GscDlpPairedFastqQuery


class BRCFastqImportStdoutView(SimpleTaskStdoutView):
    
    task_model = BRCFastqImport


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

    task_model = FileTransfer


class GscWgsBamQueryStderrView(SimpleTaskStderrView):
    
    task_model = GscWgsBamQuery


class GscDlpPairedFastqQueryStderrView(SimpleTaskStderrView):
    
    task_model = GscDlpPairedFastqQuery


class BRCFastqImportStderrView(SimpleTaskStderrView):
    
    task_model = BRCFastqImport


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
            return HttpResponseRedirect(instance.get_absolute_url())
        else:
            msg = "Failed to create the " + self.task_form.Meta.model.__name__ + ". Please fix the errors below."
            messages.error(request, msg)
        return self.get_context_and_render(request, form)


class FileTransferCreateView(SimpleTaskCreateView):

    task_form = FileTransferCreateForm


class GscWgsBamQueryCreateView(SimpleTaskCreateView):

    task_form = GscWgsBamQueryCreateForm


class GscDlpPairedFastqQueryCreateView(SimpleTaskCreateView):

    task_form = GscDlpPairedFastqQueryCreateForm


class BRCFastqImportCreateView(SimpleTaskCreateView):

    task_form = BRCFastqImportCreateForm


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
        self.task_type.apply_async(
            args=(simple_task.id,),
            queue=simple_task.get_queue_name())
        msg = "Successfully restarted the " + self.task_model.__name__ + "."
        messages.success(request, msg)
        return HttpResponseRedirect(simple_task.get_absolute_url())


class FileTransferRestartView(SimpleTaskRestartView):

    # TODO: error for starting filetransfer that is running
    task_model = FileTransfer
    task_type = tantalus.tasks.transfer_files_task


class GscWgsBamQueryRestartView(SimpleTaskRestartView):
    
    task_model = GscWgsBamQuery
    task_type = tantalus.tasks.query_gsc_wgs_bams_task


class GscDlpPairedFastqQueryRestartView(SimpleTaskRestartView):
    
    task_model = GscDlpPairedFastqQuery
    task_type = tantalus.tasks.query_gsc_dlp_paired_fastqs_task


class BRCFastqImportRestartView(SimpleTaskRestartView):
    
    task_model = BRCFastqImport
    task_type = tantalus.tasks.import_brc_fastqs_task


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
    
    task_model = FileTransfer


class GscWgsBamQueryDeleteView(SimpleTaskDeleteView):
    
    task_model = GscWgsBamQuery


class GscDlpPairedFastqQueryDeleteView(SimpleTaskDeleteView):
    
    task_model = GscDlpPairedFastqQuery


class BRCFastqImportDeleteView(SimpleTaskDeleteView):
    
    task_model = BRCFastqImport


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

    task_model = FileTransfer


class GscWgsBamQueryStopView(SimpleTaskStopView):
    
    task_model = GscWgsBamQuery


class GscDlpPairedFastqQueryStopView(SimpleTaskStopView):
    
    task_model = GscDlpPairedFastqQuery


class BRCFastqImportStopView(SimpleTaskStopView):
    
    task_model = BRCFastqImport


@method_decorator(login_required, name='dispatch')
class SampleCreate(TemplateView):

    """
    Sample create page.
    """

    template_name = "tantalus/sample_create.html"

    def get_context_and_render(self, request, form, multi_form, pk=None):
        context = {
            'pk':pk,
            'form': form,
            'multi_form': multi_form
        }
        return render(request, self.template_name, context)

    def get(self, request, *args, **kwargs):
        form = SampleForm()
        multi_form = MultipleSamplesForm()
        return self.get_context_and_render(request, form, multi_form)

    def post(self, request, *args, **kwargs):
        form = SampleForm(request.POST)
        multi_form = MultipleSamplesForm(request.POST, request.FILES)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            msg = "Successfully created the Sample."
            messages.success(request, msg)
            return HttpResponseRedirect(instance.get_absolute_url())
        elif multi_form.is_valid():
            sample_ids = multi_form.get_sample_ids()
            for sample_id in sample_ids:
                sample, created = Sample.objects.get_or_create(sample_id=sample_id)
                if created:
                    sample.save()
            return HttpResponseRedirect(sample.get_absolute_url())
        else:
            msg = "Failed to create the sample. Please fix the errors below."
            messages.error(request, msg)
            return self.get_context_and_render(request, form, multi_form)


@Render("tantalus/tag_list.html")
def tag_list(request):
    """
    List of Tags.
    """
    tags = Tag.objects.all().order_by('name')
    context = {
        'tags': tags,
    }
    return context


@method_decorator(login_required, name='dispatch')
class TagDelete(View):
    """
    Tag delete page.
    """
    def get(self, request, pk):
        get_object_or_404(Tag,pk=pk).delete()
        msg = "Successfully deleted tag"
        messages.success(request, msg)
        return HttpResponseRedirect(reverse('tag-list'))


class TagDetail(DetailView):
    model = Tag
    template_name = "tantalus/tag_detail.html"

    def get_context_data(self, object):
        tag = get_object_or_404(Tag, pk=object.id)
        datasets = [x['id'] for x in tag.abstractdataset_set.values()]
        context = {
            'tag': tag,
            'datasets':datasets,
        }
        return context


@method_decorator(login_required, name='dispatch')
class TagDatasetDelete(View):
    """
    Tag dataset delete page.
    """
    def get(self, request, pk,pk_2):
        dataset = get_object_or_404(AbstractDataSet,pk=pk)
        tag = get_object_or_404(Tag,pk=pk_2)
        tag.abstractdataset_set.remove(dataset)
        msg = "Successfully removed datasest "
        messages.success(request, msg)
        return HttpResponseRedirect(reverse('tag-detail',kwargs={'pk':pk_2}))


class DatasetListJSON(BaseDatatableView):
    
    """
    Class used as AJAX data source through the ajax option in the abstractdataset_list template.
    This enables server-side processing of the data used in the javascript DataTables.
    """
    
    model = AbstractDataSet

    columns = ['id', 'dataset_type', 'sample_id', 'library_id','library_type', 'num_read_groups', 'tags', 'storages']

    # MUST be in the order of the columns
    order_columns = ['id', 'dataset_type', 'sample_id', 'library_id','library_type', 'num_read_groups', 'tags', 'storages']
    max_display_length = 100

    def get_context_data(self, *args, **kwargs):
        dataset_pks = self.request.session.get('dataset_search_results', None)
        if dataset_pks:
            kwargs['datasets'] = dataset_pks

        self.kwargs = kwargs
        return super(DatasetListJSON, self).get_context_data(*args, **kwargs)

    def get_initial_queryset(self):
        if 'datasets' in self.kwargs.keys():
            return AbstractDataSet.objects.filter(pk__in=self.kwargs['datasets'])
        return AbstractDataSet.objects.all()

    def render_column(self, row, column):
        if column == 'dataset_type':
            return row.dataset_type_name

        if column == 'sample_id': 
            return list([sample.sample_id for sample in row.get_samples()])

        if column == 'library_id':
            return list(row.get_libraries())

        if column == 'num_read_groups':
            return row.read_groups.count()

        if column == 'tags':
            tags_string =  map(str, row.tags.all().values_list('name', flat=True))
            return tags_string

        if column == 'storages':
            return list(row.get_storage_names())

        if column == 'library_type':
            return list(row.get_library_type())

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
                        q |= Q(read_groups__sample__sample_id__startswith=search)

                    elif col['name'] == 'library_id':
                        q |= Q(read_groups__dna_library__library_id__startswith=search)

                    elif col['name'] == 'library_type':
                        q |= Q(read_groups__dna_library__library_type__startswith=search)

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

    model = AbstractDataSet
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

    model = AbstractDataSet
    template_name = "tantalus/abstractdataset_detail.html"

    def get_context_data(self, **kwargs):
        # TODO: add other fields to the view?
        context = super(DatasetDetail, self).get_context_data(**kwargs)
        context['storages'] = Storage.objects.filter(fileinstance__file_resource__in=self.object.get_file_resources()).distinct()
        return context


class DatasetSearch(FormView):
    
    form_class = DatasetSearchForm
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


class DatasetTag(FormView):
    form_class = DatasetTagForm
    template_name = 'tantalus/abstractdataset_tag_form.html'

    def get_context_data(self, **kwargs):
        
        """
        Insert the form into the context dict.
        Initialize queryset for tagging, and whether the default should have the whole queryset default to selected or not.
        """

        dataset_pks = self.request.session.get('dataset_search_results', None)
        if dataset_pks:
            datasets = AbstractDataSet.objects.filter(pk__in=dataset_pks)
            kwargs['datasets'] = datasets
        else:
            kwargs['datasets'] = AbstractDataSet.objects.all()
            kwargs['select_none_default'] = True

        if 'form' not in kwargs:
            kwargs['form'] = DatasetTagForm(datasets=dataset_pks)

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
        tag_id = Tag.objects.get(name=tag)
        self.request.session.pop('dataset_search_results', None)
        self.request.session.pop('select_none_default', None)
        return HttpResponseRedirect(reverse('tag-detail',kwargs={'pk':tag_id.id}))


class HomeView(TemplateView):
    
    template_name = 'tantalus/index.html'
    
    def get_context_data(self, **kwargs):
        context = {
            'datasets_count': AbstractDataSet.objects.count(),
            'file_transfer_count': FileTransfer.objects.all().count(),
            'gsc_wgs_bam_query_count': GscWgsBamQuery.objects.all().count(),
            'gsc_dlp_paired_fastq_query_count': GscDlpPairedFastqQuery.objects.all().count(),
            'brc_fastq_import_count': BRCFastqImport.objects.all().count(),
            'generic_task_type_count': GenericTaskType.objects.all().count(),
            'generic_task_instances_count': GenericTaskInstance.objects.all().count(),
            'sample_count': Sample.objects.all().count(),
            'transfer_count': FileTransfer.objects.all().count(),
        }
        return context
