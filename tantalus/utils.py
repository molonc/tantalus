from tantalus.models import FileTransfer, SequenceDataFile
from tasks import transfer_file


def start_transfers(deployment):
    """ Start a set of transfers for a deployment.
    """

    # get all SequenceDatasets related to this deployment
    for dataset in deployment.datasets.all():
        seq_data_files = dataset.get_data_fileset()

        #for each sequencedatafile in the SequenceDataset
        for seq_data_file in seq_data_files:
            file_instances = seq_data_file.fileinstance_set.filter(storage=deployment.to_storage)

            if len(file_instances) >= 1:
                raise ValueError('seq data {} already deployed on {}'.format(seq_data_files, deployment.to_storage))

            file_instances = seq_data_file.fileinstance_set.filter(storage=deployment.from_storage)

            if len(file_instances) == 0:
                raise ValueError('seq data {} not deployed on {}'.format(seq_data_files, deployment.from_storage))

            elif len(file_instances) > 1:
                raise ValueError('multiple seq data {} instances on {}'.format(seq_data_files, deployment.from_storage))

            # TODO: pick an ideal file instance to transfer from, rather than arbitrarily?
            file_instance = file_instances[0]

            # filter for any existing transfers involving any 1 of the file_instances for this file resource
            existing_transfers = FileTransfer.objects.filter(
                file_instance__in=file_instances,
                deployment__to_storage=deployment.to_storage)

            if len(existing_transfers) > 1:
                raise ValueError('multiple existing transfers for {} to {}'.format(seq_data_files, deployment.to_storage))

            elif len(existing_transfers) == 1:
                file_transfer = existing_transfers[0]

            else:
                file_transfer = FileTransfer()
                file_transfer.from_storage = deployment.from_storage
                file_transfer.to_storage = deployment.to_storage
                file_transfer.file_instance = file_instance
                #TODO: add tests for the naming and transfer starting
                file_transfer.new_filename = seq_data_file.default_filename
                file_transfer.save()

                transfer_file.apply_async(args=(file_transfer.id,), queue=deployment.from_storage.name)

            deployment.file_transfers.add(file_transfer)


