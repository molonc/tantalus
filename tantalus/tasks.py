from __future__ import absolute_import

from celery import shared_task, Task
from tantalus.models import Deployment, FileTransfer
import time
from azure.storage.blob import BlockBlobService
import paramiko


ACCOUNT="singlecellstorage"
KEY="okQAsp72BagVWpGLEaUNO30jH9XGLuVj3EDmbtg7oV6nmH7+9E+4csF+AXn4G3YMEKebnCnsRwVu9fRhh2RiMQ=="


@shared_task
def transfer_file(file_transfer_id):
    file_transfer = FileTransfer.objects.get(pk=file_transfer_id)

    from_storage_type = file_transfer.deployment.from_storage.__class__.__name__
    to_storage_type = file_transfer.deployment.to_storage.__class__.__name__

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
        storage=file_transfer.deployment.to_storage,
        file_resource=file_transfer.file_instance.file_resource,
        filename=file_transfer.new_filename)
    file_instance.save()

    file_transfer.running = False
    file_trasnfer.finished = True
    file_transfer.save()

    _check_deployment_complete(file_transfer.deployment)


@shared_task
def transfer_file_server_azure(file_transfer):
    block_blob_service = BlockBlobService(account_name=ACCOUNT, account_key=KEY)

    def progress_callback(current, total):
        file_transfer.progress = float(current) / float(total)

    block_blob_service.create_blob_from_path(
        file_transfer.deployment.from_storage.storage_container,
        file_transfer.new_filename,
        file_transfer.file_instance.filename,
        progress_callback=progress_callback)

    # TODO: make directory, permissions, check exists


@shared_task
def transfer_file_azure_server(file_transfer):
    block_blob_service = BlockBlobService(account_name=ACCOUNT, account_key=KEY)

    def progress_callback(current, total):
        file_transfer.progress = float(current) / float(total)

    new_filename = '?'

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
        file_transfer.deployment.to_storage.ip_address,
        username=file_transfer.deployment.to_storage.username)

    sftp = paramiko.SFTPClient.from_transport(client.get_transport())

    def progress_callback(current, total):
        file_transfer.progress = float(current) / float(total)

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

