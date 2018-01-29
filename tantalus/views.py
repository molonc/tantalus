from django.core.urlresolvers import reverse, reverse_lazy
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.generic.list import ListView
from django.views.generic import DetailView, FormView
from django.views.generic.base import TemplateView
from django.db import transaction
from django.shortcuts import get_object_or_404, render
from django_datatables_view.base_datatable_view import BaseDatatableView
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

import os

from tantalus.models import FileTransfer, FileResource, Sample, AbstractDataSet, Storage
from tantalus.utils import read_excel_sheets
from tantalus.settings import STATIC_ROOT
from misc.helpers import Render
from .forms import SampleForm, MultipleSamplesForm, DatasetSearchForm, DatasetTagForm, FileTransferCreateForm
import tantalus.tasks
from tantalus.settings import PROJECT_ROOT


@Render("tantalus/sample_list.html")
def sample_list(request):
    """list of samples."""
    samples = Sample.objects.all().order_by('sample_id')
    context = {'samples': samples}
    return context


class FileTransferListView(TemplateView):
    template_name = 'tantalus/filetransfer_list.html'
    
    def get_context_data(self, **kwargs):
        transfers = FileTransfer.objects.all()
        context = {'transfers': transfers}
        return context


def get_file_transfer_log(transfer, stderr=False, raw=False, preview_size=1000):
    if stderr:
        kind = 'stderr'
    else:
        kind = 'stdout'

    transfer_log_file_path = os.path.join(
        STATIC_ROOT,
        "logs/tasks/transfer_files/{pk}/{kind}.txt".format(
            pk=transfer.pk, kind=kind))

    if not os.path.exists(transfer_log_file_path):
        return ['unable to open ' + transfer_log_file_path]

    if raw:
        with open(transfer_log_file_path, 'r') as log_file:
            return log_file.read()

    log = []
    with open(transfer_log_file_path, 'r') as log_file:
        for i, line in enumerate(log_file):
            log.append(line)
            if preview_size is not None and len(log) >= preview_size:
                break

    return log


class FileTransferDetailView(TemplateView):
    template_name = 'tantalus/filetransfer_detail.html'

    def get_context_data(self, **kwargs):
        transfer = get_object_or_404(FileTransfer, id=kwargs['pk'])
        try:
            stdout_page, stderr_page = self.request.GET.get('page', '1,1').split(',')
        except ValueError as e:
            stdout_page, stderr_page = 1, 1

        paginator_stdout = Paginator(get_file_transfer_log(transfer), 100)
        try:
            std = paginator_stdout.page(stdout_page)
        except PageNotAnInteger:
            std = paginator_stdout.page(1)
        except EmptyPage:
            std = paginator_stdout.page(paginator_stdout.num_pages)

        paginator_stderr = Paginator(get_file_transfer_log(transfer, stderr=True), 100)
        try:
            err = paginator_stderr.page(stderr_page)
        except PageNotAnInteger:
            err = paginator_stderr.page(1)
        except EmptyPage:
            err = paginator_stderr.page(paginator_stderr.num_pages)

        context = {'transfer': transfer,
                   'std':std,
                   'err':err,
                   'pk':kwargs['pk'],
                   }

        return context


class FileTransferStdoutView(TemplateView):
    template_name = 'tantalus/filetransfer_stdout.html'

    def get_context_data(self, **kwargs):
        transfer = get_object_or_404(FileTransfer, id=kwargs['pk'])
        context = {'transfer': transfer,
                   'pk': kwargs['pk'],
                   'transfer_stdout': get_file_transfer_log(transfer, raw=True),
                   }
        return context


class FileTransferStderr(TemplateView):
    template_name = 'tantalus/filetransfer_stderr.html'

    def get_context_data(self, **kwargs):
        transfer = get_object_or_404(FileTransfer, id=kwargs['pk'])
        context = {'transfer': transfer,
                   'pk': kwargs['pk'],
                   'transfer_stderr': get_file_transfer_log(transfer, stderr=True, raw=True),
                   }
        return context
@method_decorator(login_required, name='get')


class FileTransferCreateView(TemplateView):
    template_name = 'tantalus/filetransfer_form.html'

    def get_context_and_render(self, request, form):
        context = {'form': form}
        return render(request, self.template_name, context)

    def get(self, request, *args, **kwargs):
        form = FileTransferCreateForm()
        return self.get_context_and_render(request, form)

    def post(self, request, *args, **kwargs):
        form = FileTransferCreateForm(request.POST)
        if form.is_valid():
            instance = form.save()
            return HttpResponseRedirect(instance.get_absolute_url())
        else:
            msg = "Failed to create the transfer. Please fix the errors below."
            messages.error(request, msg)
        return self.get_context_and_render(request, form)


@login_required()
def start_filetransfer(request, pk):
    transfer = get_object_or_404(FileTransfer, pk=pk)
    # TODO: error for starting filetransfer that is running
    if transfer.running:
        return
    tantalus.tasks.transfer_files_task.apply_async(
        args=(transfer.id,),
        queue=transfer.get_transfer_queue_name())
    return HttpResponseRedirect(transfer.get_absolute_url())


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


class DatasetListJSON(BaseDatatableView):
    """
    Class used as AJAX data source through the ajax option in the abstractdataset_list template.
    This enables server-side processing of the data used in the javascript DataTables.
    """
    model = AbstractDataSet

    columns = ['id', 'dataset_type', 'dna_sequences.sample.sample_id', 'dna_sequences.dna_library.library_id', 'num_lanes', 'tags', ]

    # MUST be in the order of the columns
    order_columns = ['id', 'dataset_type', 'dna_sequences.sample.sample_id', 'dna_sequences.dna_library.library_id', 'num_lanes', 'tags', ]
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

        if column == 'num_lanes':
            return row.lanes.count()

        if column == 'tags':
            tags_string =  map(str, row.tags.all().values_list('name', flat=True))
            return tags_string

        else:
            return super(DatasetListJSON, self).render_column(row, column)

    def filter_queryset(self, qs):
        """ If search['value'] is provided then filter all searchable columns using istartswith
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

                    # standard search for simple . lookups across models
                    else:
                        # apply global search to all searchable columns
                        q |= Q(**{'{0}__startswith'.format(self.columns[col_no].replace('.', '__')): search})
                        # column specific filter
                        if col['search.value']:
                            qs = qs.filter(**{'{0}__startswith'.format(self.columns[col_no].replace('.', '__')): col['search.value']})

            qs = qs.filter(q)
        return qs


class DatasetList(ListView):

    model = AbstractDataSet
    template_name = "tantalus/abstractdataset_list.html"
    paginate_by = 100

    class Meta:
        ordering = ["id"]

    def get_context_data(self, **kwargs):
        # TODO: add other fields to the view?
        """ get context data, and pop session variables from search/tagging if they exist """
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
        storages = Storage.objects.filter(fileinstance__file_resource__in=self.object.get_data_fileset()).distinct()
        context['storages'] = storages
        return context


class DatasetSearch(FormView):
    form_class = DatasetSearchForm
    success_url = reverse_lazy('dataset-tag')
    template_name = 'tantalus/abstractdataset_search_form.html'

    def post(self, request, *args, **kwargs):
        """
            Handles POST requests, instantiating a form instance with the passed
            POST variables and then checked for validity.
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
    success_url = reverse_lazy('dataset-list')

    def get_context_data(self, **kwargs):
        """
        Insert the form into the context dict. Initialize queryset for tagging, and whether the default should have
        the whole queryset default to selected or not.
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

        self.request.session.pop('dataset_search_results', None)
        self.request.session.pop('select_none_default', None)
        return super(DatasetTag, self).form_valid(form)


class HomeView(TemplateView):
    template_name = 'tantalus/index.html'
    
    def get_context_data(self, **kwargs):
        context = {
            'datasets_count': AbstractDataSet.objects.count(),
            'filetransfer_count': FileTransfer.objects.all().count(),
            'sample_count': Sample.objects.all().count(),
            'transfer_count': FileTransfer.objects.all().count()
        }
        return context
