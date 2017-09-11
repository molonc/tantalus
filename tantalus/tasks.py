from __future__ import absolute_import

from celery import shared_task, Task
import tantalus.models
from tantalus.file_transfer_utils import *


@shared_task
def transfer_file(file_transfer_id):
    file_transfer = tantalus.models.FileTransfer.objects.get(pk=file_transfer_id)

    from_storage_type = file_transfer.from_storage.__class__.__name__
    to_storage_type = file_transfer.to_storage.__class__.__name__
    file_transfer.running = True
    file_transfer.save()

    if from_storage_type == 'ServerStorage' and to_storage_type == 'AzureBlobStorage':
        transfer_file_server_azure(file_transfer)
        print "cloud"

    elif from_storage_type == 'AzureBlobStorage' and to_storage_type == 'ServerStorage':
        transfer_file_azure_server(file_transfer)
        print "cloud"

    elif from_storage_type == 'ServerStorage' and to_storage_type == 'ServerStorage':
        transfer_file_server_server(file_transfer)
        print "server"

    else:
        raise Exception('unsupported transfer')

    for deployment in file_transfer.deployment_set.all():
        _check_deployment_complete(deployment)


@shared_task
def transfer_file_server_azure(file_transfer):
    try:
        perform_transfer_file_server_azure(file_transfer)
    except:
        print "helpful error message thrown here"
        raise
    # TODO: make directory, permissions, check exists


@shared_task
def transfer_file_azure_server(file_transfer):
    try:
        perform_transfer_file_azure_server(file_transfer)
    except:
        print "helpful error message thrown here"
        raise
    # TODO: make directory, permissions, check exists


@shared_task
def transfer_file_server_server(file_transfer):
    try:
        perform_transfer_file_server_server(file_transfer)
    except:
        print "helpful error message thrown here"
        raise
    # TODO: make directory, permissions, check exists


def _check_deployment_complete(deployment):
    for file_transfer in deployment.file_transfers.all():
        if file_transfer.finished and not file_transfer.success:
            deployment.errors = True
    deployment.save()

    for file_transfer in deployment.file_transfers.all():
        if not file_transfer.finished:
            return

    deployment.finished = True
    deployment.save()

