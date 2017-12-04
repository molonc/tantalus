import xlrd
from django.core.urlresolvers import reverse, reverse_lazy
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic import DetailView, FormView
from django.views.generic.edit import ModelFormMixin, View
from django.views.generic.base import TemplateView
from django.db import transaction
from django.shortcuts import get_object_or_404, render
import django.forms

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


class DatasetList(ListView):

    model = AbstractDataSet

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
