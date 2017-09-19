from django.contrib import messages
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView
from django.views.generic.edit import ModelFormMixin
from django.db import transaction
from tantalus.models import FileTransfer, Deployment, FileResource
from tasks import transfer_file
from tantalus.utils import create_deployment_file_transfers

class FileTransferListView(ListView):
    model = FileTransfer
    template_name="tantalus/transfer_list.html"


class DeploymentListView(ListView):
    model = Deployment


class DeploymentCreateView(CreateView):
    model = Deployment
    fields = ['from_storage', 'to_storage', 'datasets']

    def post(self, request, *args, **kwargs):
        try:
            self.object = None
            with transaction.atomic():
                form = self.get_form()
                if form.is_valid():
                    self.object = form.save()
                    self.object.state = 'Started'
                    self.object.save()

                    file_transfer_ids = []

                    deployment = self.object
                    create_deployment_file_transfers(deployment)
                    return super(ModelFormMixin, self).form_valid(form)
        except ValueError as e:
            error_message = ' '.join(e.args)
            messages.error(request, error_message)
            #TODO: override methods + update template so that error message is passed through and is useful
        return self.form_invalid(form)

