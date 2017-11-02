from __future__ import absolute_import
from django.db import transaction
from tantalus.models import FileTransfer
from tantalus.exceptions.api_exceptions import DeploymentNotCreated
from tantalus.exceptions.file_transfer_exceptions import DeploymentUnnecessary
import tantalus.tasks
from celery import chain
import pandas as pd


def start_file_transfer(file_transfer, deployment):
    """
    Start a single file transfer.
    """

    from_storage_type = file_transfer.from_storage.__class__.__name__
    to_storage_type = file_transfer.to_storage.__class__.__name__

    if from_storage_type == 'ServerStorage' and to_storage_type == 'AzureBlobStorage':
        tantalus.tasks.transfer_file_server_azure_task.apply_async(args=(file_transfer.id,), queue=deployment.from_storage.get_transfer_queue_name())

    elif from_storage_type == 'AzureBlobStorage' and to_storage_type == 'ServerStorage':
        make_dirs_sig = tantalus.tasks.make_dirs_for_file_transfer_task.signature((file_transfer.id,), immutable=True)
        make_dirs_sig.set(queue=deployment.to_storage.get_mkdir_queue_name())
        transfer_file_sig = tantalus.tasks.transfer_file_azure_server_task.signature((file_transfer.id,), immutable=True)
        transfer_file_sig.set(queue=deployment.to_storage.get_transfer_queue_name())
        chain(make_dirs_sig, transfer_file_sig).apply_async()

    elif from_storage_type == 'ServerStorage' and to_storage_type == 'ServerStorage':
        make_dirs_sig = tantalus.tasks.make_dirs_for_file_transfer_task.signature((file_transfer.id,), immutable=True)
        make_dirs_sig.set(queue=deployment.to_storage.get_mkdir_queue_name())
        transfer_file_sig = tantalus.tasks.transfer_file_server_server_task.signature((file_transfer.id,), immutable=True)
        transfer_file_sig.set(queue=deployment.to_storage.get_transfer_queue_name())
        chain(make_dirs_sig, transfer_file_sig).apply_async()

    else:
        raise Exception('unsupported transfer')


def start_file_transfers(file_transfers, deployment):
    """
    Start a set of file transfers.
    """

    for file_transfer in file_transfers:
        start_file_transfer(file_transfer, deployment)


def create_deployment_file_transfers(deployment, restart=False):
    """ 
    Create a set of transfers for a deployment.
    """

    files_to_transfer = []
    # get all AbstractDataSets related to this deployment
    for dataset in deployment.datasets.all():
        file_resources = dataset.get_data_fileset()

        for file_resource in file_resources:
            destination_file_instances = file_resource.fileinstance_set.filter(storage=deployment.to_storage)

            if len(destination_file_instances) >= 1:
                continue

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
                raise DeploymentNotCreated('multiple existing transfers for {} to {}'.format(file_resource.filename, deployment.to_storage))

            elif len(existing_transfers) == 1:
                file_transfer = existing_transfers[0]

                if file_transfer.finished and not file_transfer.success:
                    files_to_transfer.append(file_transfer)
                elif restart and not file_transfer.success:
                    files_to_transfer.append(file_transfer)

            else:
                file_transfer = FileTransfer()
                file_transfer.from_storage = deployment.from_storage
                file_transfer.to_storage = deployment.to_storage
                file_transfer.file_instance = file_instance
                #TODO: add tests for the naming and transfer starting
                file_transfer.save()

                files_to_transfer.append(file_transfer)

            # except: #ADD EXCEPTION THROWN FROM SIGNAL
            #     pass

            # add exception handling for when ???


            deployment.file_transfers.add(file_transfer)

    return files_to_transfer


def start_deployment(deployment, restart=False):
    """ 
    Start a set of transfers for a deployment.
    """

    with transaction.atomic():
        files_to_transfer = create_deployment_file_transfers(deployment, restart=restart)

        if len(files_to_transfer) == 0:
            raise DeploymentUnnecessary()

        transaction.on_commit(lambda: start_file_transfers(files_to_transfer, deployment))


def read_excel_sheets(filename):
    """ 
    Load and read an excel file, extracting specific columns.
    """
    
    required_columns = ['sample_id']

    try:
        data = pd.read_excel(filename, sheetname=None)
    except IOError:
        raise ValueError('Unable to find file', filename)
    
    # convert all column names in the loaded file to lowercase
    for sheetname in data:
            data[sheetname].columns = [c.lower() for c in data[sheetname].columns]

    for sheetname in data:
        if set(required_columns).issubset(data[sheetname].columns):
            yield data[sheetname]


def start_md5_checks(file_instances):
    """
    Start md5 check jobs on file instances.
    """

    for file_instance in file_instances:
        md5_check = tantalus.models.MD5Check(
            file_instance=file_instance
        )
        md5_check.save()

        tantalus.tasks.check_md5_task.apply_async(args=(md5_check.id,), queue=file_instance.storage.get_md5_queue_name())


