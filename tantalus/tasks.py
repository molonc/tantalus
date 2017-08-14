from __future__ import absolute_import

from celery import shared_task, Task
from tantalus.models import Deployment, FileTransfer
import time
from misc.blob_demo import get_service
import paramiko


@shared_task
def run_cloud_transfer(file_to_transfer, file_transfers, deployment, container_name, blob_name):
    print 'sleeping'
    time.sleep(30)
    print 'finished'

    service = get_service()
    # upload a file to the cloud
    service.create_blob_from_path(
        container_name,  # name of container
        blob_name,  # name of the blob
        "/Users/jngo/Desktop/favicon.png")

    ## UPDATE FILETRANSFER OBJECT

    service.get_blob_to_path(container_name,blob_name,(blob_name+'.png'))

    _update_filetransfer_status(file_to_transfer)
    _check_transfer_complete(file_transfers, deployment)
    return 100

@shared_task
def run_server_transfer(file_to_transfer, file_transfers, deployment):
    print 'sleeping'
    time.sleep(15)
    paramiko.util.log_to_file("just-1-more.log")

    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.connect('beast.cluster.bccrc.ca') # replace with server of source files
    stdin, stdout, stderr = client.exec_command(
        'rsync -avPL {source_path} {remote_host}:{destination_parent_dir}'.format(
            source_path = "~/scptest", # path of file directory/file
            remote_host = "10.9.208.161", # hostname of server - eg. thost is 10.9.208.161
            destination_parent_dir ="~/", # parent directory of destination for file transfers
        ))
    for line in stdout:
        print line.strip("\n")
    print 'finished'

    client.close()
    _update_filetransfer_status(file_to_transfer)
    _check_transfer_complete(file_transfers, deployment)
    return 300

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

