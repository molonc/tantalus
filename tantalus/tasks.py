from __future__ import absolute_import

from celery import shared_task, Task
from tantalus.models import Deployment, FileTransfer
import time
from misc.blob_demo import get_service


@shared_task
def run_cloud_transfer(file_to_transfer, file_transfers, deployment, container_name, blob_name):
    print 'sleeping'
    time.sleep(15)
    print 'finished'

    service = get_service()
    # upload a file to the cloud
    service.create_blob_from_path(
        container_name,  # name of container
        blob_name,  # name of the blob
        "/Users/jngo/Desktop/favicon.png")

    ## UPDATE FILETRANSFER OBJECT

    _update_filetransfer_status(file_to_transfer)
    _check_transfer_complete(file_transfers, deployment)
    return 100

@shared_task
def run_server_transfer(file_to_transfer, file_transfers, deployment):
    print 'sleeping'
    time.sleep(15)
    print 'finished'

    # upload a file to the cloud
    # service.create_blob_from_path(
    #     container_name,  # name of container
    #     blob_name,  # name of the blob
    #     "/Users/jngo/Desktop/favicon.png")

    ## UPDATE FILETRANSFER OBJECT

    _update_filetransfer_status(file_to_transfer)
    _check_transfer_complete(file_transfers, deployment)
    return 100

def _update_filetransfer_status(file_to_transfer):
    file_to_transfer = FileTransfer.objects.get(pk=file_to_transfer)
    file_to_transfer.state = 'Finished'
    file_to_transfer.result = 100
    file_to_transfer.save()

def _check_transfer_complete(file_transfers, deployment):
    print "checking if task is complete for {}".format(file_transfers)
    if map(str, FileTransfer.objects.filter(id__in=file_transfers).values_list('state', flat=True).distinct()) != ['Finished']:
        print "task still in progress"
    else:
        deployment = Deployment.objects.get(pk = deployment)
        deployment.state = 'Finished'
        deployment.result = 200
        deployment.save()
        print "task complete"
    return 200

