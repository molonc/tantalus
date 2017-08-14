from django.views.generic.list import ListView
from django.views.generic.edit import CreateView
from django.views.generic.edit import ModelFormMixin
from tantalus.models import FileTransfer, Deployment, BamFile, PairedEndFastqFiles, SingleEndFastqFile, SequenceDataFile
from tantalus.tasks import run_cloud_transfer, run_server_transfer
from misc.blob_demo import get_service


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

            # creating file transfer object for each file in the deployment
            for sequencedatafile in self.object.datasets.all().values_list('sequence_data', flat=True):
                ft = FileTransfer(
                    deployment=self.object,
                    state="Started",
                    datafile=SequenceDataFile.objects.get(pk=sequencedatafile)
                    # result=100 #TODO: replace this with real path
                )
                ft.save()
                file_transfer_ids.append(ft.id)

            print self.object.to_storage.__class__.__name__  # type of storage

            # File transfer to cloud storage
            if (self.object.to_storage.__class__.__name__) == "AzureBlobStorage":
                service = get_service()
                container_name = self.object.to_storage.storage_container
                # service.create_container(container_name) ## TODO: can assume container is already created?

                # appended select_related so that django ORM doesnt hit the database a second time to query for the related SequenceDataFile object
                for file_to_transfer in self.object.filetransfer_set.select_related('datafile'):
                    blob_name = file_to_transfer.datafile.md5
                    # upload a file to the container
                    run_cloud_transfer.delay(file_to_transfer.id, file_transfer_ids, self.object.id, container_name, blob_name)
                ### TODO: This is for cleaning up while in development - remove this when cloud is ready
                for blob in service.list_blobs(container_name):
                    print (blob.name)
                    service.delete_blob(container_name, blob.name)

            # File transfer to server
            else:
                for file_to_transfer in self.object.filetransfer_set.all():
                    run_server_transfer.delay(file_to_transfer.id, file_transfer_ids, self.object.id)

            return super(ModelFormMixin, self).form_valid(form)
        else:
            return self.form_invalid(form)


