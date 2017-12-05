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

from tantalus.models import FileTransfer, Deployment, FileResource, Sample, AbstractDataSet, Storage
from tantalus.utils import read_excel_sheets, add_file_transfers, start_file_transfers, initialize_deployment
from tantalus.exceptions.api_exceptions import DeploymentNotCreated
from misc.helpers import Render
from .forms import SampleForm, MultipleSamplesForm, DatasetSearchForm, DatasetTagForm, DeploymentCreateForm


def search_view(request):
    query_str = request.GET.get('query_str')
    instance = None

    # search for samples
    if Sample.objects.filter(sample_id=query_str):
        instance = Sample.objects.filter(sample_id=query_str)[0]

    if instance:
        return HttpResponseRedirect(instance.get_absolute_url())
    else:
        msg = "Sorry, no match found."
        messages.warning(request, msg)
        return HttpResponseRedirect(reverse('home'))

@Render("tantalus/sample_list.html")
def sample_list(request):
    """list of samples."""
    samples = Sample.objects.all().order_by('sample_id')
    context = {'samples': samples}
    return context

#============================
# Classes
#----------------------------
class FileTransferView(TemplateView):
    template_name = 'tantalus/filetransfer_list.html'
    
    def get_context_data(self, **kwargs):
        transfers = FileTransfer.objects.all()
        context = {'transfers': transfers}
        return context


class DeploymentDetailView(TemplateView):
    template_name = 'tantalus/deployment_detail.html'
    
    def get_context_data(self, **kwargs):
        deployment = get_object_or_404(Deployment, id=kwargs['pk'])
        context = {'deployment': deployment}
        return context


class DeploymentView(TemplateView):
    template_name = 'tantalus/deployment_list.html'
    
    def get_context_data(self, **kwargs):
        deployments = Deployment.objects.all()
        context = {'deployments': deployments}
        return context


@method_decorator(login_required, name='get')
class DeploymentCreateView(TemplateView):
    template_name = 'tantalus/deployment_form.html'

    def get_context_and_render(self, request, form):
        context = {'form': form}
        return render(request, self.template_name, context)

    def get(self, request, *args, **kwargs):
        form = DeploymentCreateForm()
        return self.get_context_and_render(request, form)

    def post(self, request, *args, **kwargs):
        form = DeploymentCreateForm(request.POST)
        if form.is_valid():
            instance = form.save()
            return HttpResponseRedirect(instance.get_absolute_url())
        else:
            msg = "Failed to create the deployment. Please fix the errors below."
            messages.error(request, msg)
        return self.get_context_and_render(request, form)


@login_required()
def start_deployment(request, pk):
    deployment = get_object_or_404(Deployment, pk=pk)
    # TODO: error for starting deployment that is running
    if deployment.running:
        return
    with transaction.atomic():
        initialize_deployment(deployment)
        transaction.on_commit(lambda: start_file_transfers(deployment=deployment))
    return HttpResponseRedirect(deployment.get_absolute_url())


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

    columns = ['id', 'file_resource', 'file_type', 'dna_sequences.sample.sample_id', 'dna_sequences.dna_library.library_id', 'tags', ]

    # MUST be in the order of the columns
    order_columns = ['id', 'file_resource', 'file_type', 'dna_sequences.sample.sample_id', 'dna_sequences.dna_library.library_id', 'tags', ]
    max_display_length = 100

    def get_initial_queryset(self):
        return AbstractDataSet.objects.all()

    def render_column(self, row, column):
        if column == 'file_type':
            file_resource_string = ""
            for file_resource in row.get_data_fileset():
                file_resource_string = file_resource_string + file_resource.get_file_type_display() + "\n"
            return file_resource_string

        elif column == 'file_resource':
            file_resource_string = ""
            for file_resource in row.get_data_fileset():
                file_resource_string = file_resource_string + file_resource.filename + "\n"
            return file_resource_string

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
                    elif col['name'] == 'file_type':
                        q = q | Q(bamfile__bam_file__file_type__iexact=search) | Q(singleendfastqfile__reads_file__file_type__iexact=search) | Q(pairedendfastqfiles__reads_1_file__file_type__iexact=search)
                    elif col['name'] == 'file_resource':
                        q = q | Q(bamfile__bam_file__filename__startswith=search) | Q(singleendfastqfile__reads_file__filename__startswith=search) | Q(pairedendfastqfiles__reads_1_file__filename__startswith=search)
                        q = q | Q(bamfile__bam_index_file__filename__startswith=search) | Q(pairedendfastqfiles__reads_2_file__filename__startswith=search)

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
            'deployment_count': Deployment.objects.all().count(),
            'sample_count': Sample.objects.all().count(),
            'transfer_count': FileTransfer.objects.all().count()
        }
        return context
