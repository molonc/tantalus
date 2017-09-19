from tantalus.models import FileTransfer
# from tasks import transfer_file


def create_deployment_file_transfers(deployment):
    """ Start a set of transfers for a deployment.
    """

    # get all AbstractFileSets related to this deployment
    for dataset in deployment.datasets.all():
        file_resources = dataset.get_data_fileset()

        #for each fileresource in the fileset
        for file_resource in file_resources:
            file_instances = file_resource.fileinstance_set.filter(storage=deployment.to_storage)

            if len(file_instances) >= 1:
                raise ValueError('file resource {} already deployed on {}'.format(file_resource.filename, deployment.to_storage))

            file_instances = file_resource.fileinstance_set.filter(storage=deployment.from_storage)

            if len(file_instances) == 0:
                raise ValueError('seq data {} not deployed on {}'.format(file_resource.filename, deployment.from_storage))

            elif len(file_instances) > 1:
                raise ValueError('multiple seq data {} instances on {}'.format(file_resource.filename, deployment.from_storage))

            # TODO: pick an ideal file instance to transfer from, rather than arbitrarily?
            file_instance = file_instances[0]

            # filter for any existing transfers involving any 1 of the file_instances for this file resource
            existing_transfers = FileTransfer.objects.filter(
                file_instance__in=file_instances,
                deployment__to_storage=deployment.to_storage)

            if len(existing_transfers) > 1:
                raise ValueError('multiple existing transfers for {} to {}'.format(file_resource.filename, deployment.to_storage))

            elif len(existing_transfers) == 1:
                file_transfer = existing_transfers[0]

            else:
                file_transfer = FileTransfer()
                file_transfer.from_storage = deployment.from_storage
                file_transfer.to_storage = deployment.to_storage
                file_transfer.file_instance = file_instance
                #TODO: add tests for the naming and transfer starting
                file_transfer.new_filename = file_resource.filename
                file_transfer.save()


            deployment.file_transfers.add(file_transfer)


