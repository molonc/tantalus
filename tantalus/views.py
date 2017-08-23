from django.views.generic.list import ListView
from django.views.generic.edit import CreateView
from django.views.generic.edit import ModelFormMixin
from django.db import transaction
from tantalus.models import FileTransfer, Deployment, SequenceDataFile
from tasks import transfer_file


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
            with transaction.atomic():
                form = self.get_form()
                if form.is_valid():
                    self.object = form.save()
                    self.object.state = 'Started'
                    self.object.save()

                    file_transfer_ids = []

                    deployment = self.object
                    start_transfers(deployment)
                    return super(ModelFormMixin, self).form_valid(form)
        except ValueError as e:
            error_message = ' '.join(e.args)
            #TODO: override methods + update template so that error message is passed through and is useful
            return self.form_invalid(form)


def start_transfers(deployment):
    """ Start a set of transfers for a deployment.
    """

    for seq_data_id in deployment.datasets.all().select_related('sequence_data').values_list('sequence_data', flat=True):
        seq_data = SequenceDataFile.objects.get(id=seq_data_id)

        file_instances = seq_data.fileinstance_set.filter(storage=deployment.from_storage)

        if len(file_instances) == 0:
            raise ValueError('seq data {} not deployed on {}'.format(seq_data, deployment.from_storage))

        elif len(file_instances) > 1:
            raise ValueError('multiple seq data {} instances on {}'.format(seq_data, deployment.from_storage))

        file_instance = file_instances[0]

        existing_transfers = FileTransfer.objects.filter(
            file_instance=file_instance,
            deployment__to_storage=deployment.to_storage)

        if len(existing_transfers) > 1:
            raise ValueError('multiple existing transfers for {} to {}'.format(seq_data, deployment.to_storage))

        elif len(existing_transfers) == 1:
            file_transfer = existing_transfers[0]

        else:
            file_transfer = FileTransfer(
                deployment=deployment,
                file_instance=file_instance,
                new_filename=seq_data.default_filename)
            file_transfer.save()

            transfer_file.apply_async(args=(file_transfer.id,), queue=deployment.from_storage.name)

        deployment.file_transfers.add(file_transfer)


