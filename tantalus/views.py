from django.views.generic.list import ListView
from django.views.generic.edit import CreateView
from django.views.generic.edit import ModelFormMixin
from tantalus.models import FileTransfer, Deployment


class FileTransferListView(ListView):
    model = FileTransfer


class DeploymentListView(ListView):
    model = Deployment


class DeploymentCreateView(CreateView):
    model = Deployment
    fields = ['from_storage', 'to_storage', 'datasets']

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            self.object = form.save()
            self.object.state = 'Started'
            self.object.save()

            file_transfer_ids = []

            deployment = self.object

            try:
                start_transfers(deployment)
            except ValueError as e:
                pass
                # TODO: set error
                
            return super(ModelFormMixin, self).form_valid(form)
        else:
            return self.form_invalid(form)


def start_transfers(deployment):
    """ Start a set of transfers for a deployment.
    """

    for seq_data in deployment.datasets.all().values_list('sequence_data', flat=True):
        file_instances = seq_data.fileinstance_set.filter(storage=deployment.from_storage)

        if len(file_instances) == 0:
            raise ValueError('seq data {} not deployed on {}'.format(seq_data, deployment.from_storage))

        elif len(file_instances) > 1:
            raise ValueError('multiple seq data {} instances on {}'.format(seeq_data, deployment.from_storage))

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
                state="Started",
                file_instance=file_instance,
                new_filename=seq_data.default_filename)
            file_transfer.save()

            transfer_file.delay(file_transfer, queue=deployment.from_storage.name)

        deployement.file_transfers.add(existing_transfers[0])


