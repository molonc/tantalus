from __future__ import absolute_import

from celery import shared_task, Task
import tantalus.models
import time
from azure.storage.blob import BlockBlobService
import paramiko


@shared_task
def transfer_file(file_transfer_id):
    file_transfer = tantalus.models.FileTransfer.objects.get(pk=file_transfer_id)

    from_storage_type = file_transfer.from_storage.__class__.__name__
    to_storage_type = file_transfer.to_storage.__class__.__name__

    file_transfer.running = True
    file_transfer.save()

    if from_storage_type == 'ServerStorage' and to_storage_type == 'AzureBlobStorage':
        transfer_file_server_azure(file_transfer)

    elif from_storage_type == 'AzureBlobStorage' and to_storage_type == 'ServerStorage':
        transfer_file_azure_server(file_transfer)

    elif from_storage_type == 'ServerStorage' and to_storage_type == 'ServerStorage':
        transfer_file_server_server(file_transfer)

    else:
        raise Exception('unsupported transfer')

    file_instance = tantalus.models.FileInstance(
        storage=file_transfer.to_storage,
        file_resource=file_transfer.file_instance.file_resource,
        filename=file_transfer.new_filename)
    file_instance.save()

    file_transfer.running = False
    file_transfer.finished = True
    file_transfer.save()

    for deployment in file_transfer.deployment_set.all():
        _check_deployment_complete(deployment)


@shared_task
def transfer_file_server_azure(file_transfer):
    block_blob_service = BlockBlobService(
        account_name=file_transfer.to_storage.storage_account,
        account_key=file_transfer.to_storage.storage_key)

    def progress_callback(current, total):
        file_transfer.progress = float(current) / float(total)
        file_transfer.save()

    block_blob_service.create_blob_from_path(
        file_transfer.to_storage.storage_container,
        file_transfer.new_filename,
        file_transfer.file_instance.filename,
        progress_callback=progress_callback)

    # TODO: make directory, permissions, check exists


@shared_task
def transfer_file_azure_server(file_transfer):
    block_blob_service = BlockBlobService(
        account_name=file_transfer.from_storage.storage_account,
        account_key=file_transfer.from_storage.storage_key)

    def progress_callback(current, total):
        file_transfer.progress = float(current) / float(total)
        file_transfer.save()

    block_blob_service.get_blob_to_path(
        file_transfer.from_storage.storage_container,
        file_transfer.file_instance.filename,
        file_transfer.new_filename,
        progress_callback=progress_callback)

    # TODO: make directory, permissions, check exists


@shared_task
def transfer_file_server_server(file_transfer):
    client = paramiko.SSHClient()
    client.load_system_host_keys()

    client.connect(
        file_transfer.to_storage.ip_address,
        username=file_transfer.to_storage.username)

    sftp = paramiko.SFTPClient.from_transport(client.get_transport())

    def progress_callback(current, total):
        file_transfer.progress = float(current) / float(total)
        file_transfer.save()

    sftp.put(
        file_transfer.file_instance.filename,
        file_transfer.new_filename,
        callback=progress_callback)

    # TODO: make directory, permissions, check exists


def _check_deployment_complete(deployment):
    for file_transfer in deployment.file_transfers:
        if file_transfer.failed:
            deployment.errors = True
    deployment.save()

    for file_transfer in deployment.file_transfers:
        if not file_transfer.finished:
            return

    deployment.finished = True
    deployment.save()

