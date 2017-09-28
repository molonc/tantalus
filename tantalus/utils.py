from tantalus.models import FileTransfer
from tantalus.exceptions.api_exceptions import DeploymentNotCreated


def create_deployment_file_transfers(deployment):
    """ Start a set of transfers for a deployment.
    """

    files_to_transfer = []
    # get all AbstractDataSets related to this deployment
    for dataset in deployment.datasets.all():
        file_resources = dataset.get_data_fileset()

        for file_resource in file_resources:
            destination_file_instances = file_resource.fileinstance_set.filter(storage=deployment.to_storage)

            if len(destination_file_instances) >= 1:
                raise DeploymentNotCreated('file instance for file resource {} already deployed on {}'.format(file_resource.filename, deployment.to_storage))

            source_file_instance = file_resource.fileinstance_set.filter(storage=deployment.from_storage)

            if len(source_file_instance) == 0:
                raise DeploymentNotCreated('file instance for file resource {} not deployed on source storage {}'.format(file_resource.filename, deployment.from_storage))

            # paranoia check - this if statement should never be able to run
            elif len(source_file_instance) > 1:
                raise DeploymentNotCreated('multiple file instances for file resource {} instances on {}'.format(file_resource.filename, deployment.from_storage))

            # TODO: pick an ideal file instance to transfer from, rather than arbitrarily?
            file_instance = source_file_instance[0]

            # filter for any existing transfers involving any 1 of the file_instances for this file resource
            existing_transfers = FileTransfer.objects.filter(
                file_instance__in=file_resource.fileinstance_set.all(),
                to_storage=deployment.to_storage)

            if len(existing_transfers) > 1:
                raise DeploymentNotCreated('multiple existing transfers for {} to {} - Contact database admin'.format(file_resource.filename, deployment.to_storage))

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

                files_to_transfer.append(file_transfer)

            # except: #ADD EXCEPTION THROWN FROM SIGNAL
            #     pass

            # add exception handling for when ???


            deployment.file_transfers.add(file_transfer)

    return files_to_transfer
