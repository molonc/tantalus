from tantalus.models import FileTransfer, SequenceDataFile
from tasks import transfer_file

def start_transfers(deployment):
    """ Start a set of transfers for a deployment.
    """
    for seq_data_id in deployment.datasets.all().select_related('sequence_data').values_list('sequence_data', flat=True):
        seq_data = SequenceDataFile.objects.get(id=seq_data_id)

        file_instances = seq_data.fileinstance_set.filter(storage=deployment.to_storage)

        if len(file_instances) >= 1:
            raise ValueError('seq data {} already deployed on {}'.format(seq_data, deployment.to_storage))

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
            file_transfer = FileTransfer()
            file_transfer.from_storage = deployment.from_storage
            file_transfer.to_storage = deployment.to_storage
            file_transfer.file_instance = file_instance
            file_transfer.new_filename = file_instance.filename  # seq_data.default_filename # not a valid method? cannot call from super class
            file_transfer.save()

            transfer_file.apply_async(args=(file_transfer.id,), queue=deployment.from_storage.name)

        deployment.file_transfers.add(file_transfer)
