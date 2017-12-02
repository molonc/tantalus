from azure.storage.blob import BlockBlobService
import paramiko
import custom_paramiko
import time
import subprocess
from django.db.models.signals import post_save
from django.dispatch import receiver

from tantalus.models import *
from tantalus.exceptions.file_transfer_exceptions import *
import tantalus.custom_shutils
import errno


# if available memory on the storage is less than this, include this as a possible source of error if the transfer fails
__MINIMUM_FREE_DISK_SPACE = 50e10


class MD5CheckError(Exception):
    pass


def get_file_md5(filepath):
    try:
        md5 = subprocess.check_output(['md5sum', filepath]).split()[0]
    except Exception as e:
        raise MD5CheckError('Unable to run md5sum on {}\n{}'.format(filepath, str(e)))
    return md5


def get_blob_md5(block_blob_service, container, blobname):
    # Try 3 times to deal with null md5 on new blobs 
    for i in range(3):
        base_64_md5 = block_blob_service.get_blob_properties(
            container,
            blobname).properties.content_settings.content_md5

        if base_64_md5 is not None:
            break

        time.sleep(10)

    # the md5 for an empty file is a NoneType object
    if base_64_md5 is None:
        md5 = "d41d8cd98f00b204e9800998ecf8427e"
    else:
        md5 = base_64_md5.decode("base64").encode("hex")

    return md5


def check_or_update_md5(md5_check):
    """ Check or update an md5 for a file instance in an md5 check object.
    """

    filepath = md5_check.file_instance.get_filepath()

    md5 = get_file_md5(filepath)
    existing_md5 = md5_check.file_instance.file_resource.md5

    if existing_md5 is None or existing_md5 == '':
        md5_check.file_instance.file_resource.md5 = md5
        md5_check.file_instance.file_resource.save()

    else:
        if existing_md5 != md5:
            raise MD5CheckError('Calculated md5 {} different from recorded md5 {} for file {}'.format(
                md5, existing_md5, filepath))


def create_file_instance(file_transfer):
    file_instance = FileInstance(
        storage=file_transfer.to_storage,
        file_resource=file_transfer.file_instance.file_resource,)
    file_instance.save()


def get_block_blob_service(storage):
    block_blob_service = BlockBlobService(
        account_name=storage.storage_account,
        account_key=storage.credentials.storage_key)
    return block_blob_service


def make_dirs_for_file_transfer(file_transfer):
    filepath = file_transfer.get_filepath()
    dirname = os.path.dirname(filepath)
    try:
        os.makedirs(dirname)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def transfer_file_azure_server(file_transfer):
    """ Transfer a file from a server to blob.
    
    This should be called on the to server.
    """

    block_blob_service = get_block_blob_service(storage=file_transfer.file_instance.storage)

    cloud_filepath = file_transfer.file_instance.get_filepath()
    cloud_container, cloud_blobname = cloud_filepath.split('/', 1)
    assert cloud_container == file_transfer.file_instance.storage.get_storage_container()
    local_filepath = file_transfer.get_filepath()

    if not block_blob_service.exists(cloud_container, cloud_blobname):
        error_message = "source file {filepath} does not exist on {storage} for file instance with pk: {pk}".format(
            filepath=cloud_filepath,
            storage=file_transfer.file_instance.storage.name,
            pk=file_transfer.file_instance.id)
        raise FileDoesNotExist(error_message)

    if os.path.isfile(local_filepath):
        error_message = "target file {filepath} already exists on {storage}".format(
            filepath=local_filepath,
            storage=file_transfer.file_instance.storage.name)
        raise FileAlreadyExists(error_message)

    def progress_callback(current, total):
        if total != 0:
            file_transfer.progress = float(current) / float(total)
            file_transfer.save()

    block_blob_service.get_blob_to_path(
        cloud_container,
        cloud_blobname,
        local_filepath,
        progress_callback=progress_callback)

    create_file_instance(file_transfer)
    os.chmod(local_filepath, 0444)


def transfer_file_server_azure(file_transfer):
    """ Transfer a file from a server to blob.
    
    This should be called on the from server.
    """

    block_blob_service = get_block_blob_service(storage=file_transfer.to_storage)

    local_filepath = file_transfer.file_instance.get_filepath()
    cloud_filepath = file_transfer.get_filepath()
    cloud_container, cloud_blobname = cloud_filepath.split('/', 1)
    assert cloud_container == file_transfer.to_storage.get_storage_container()

    if not os.path.isfile(local_filepath):
        error_message = "source file {filepath} does not exist on {storage} for file instance with pk: {pk}".format(
            filepath=local_filepath,
            storage=file_transfer.file_instance.storage.name,
            pk=file_transfer.file_instance.id)
        raise FileDoesNotExist(error_message)

    if block_blob_service.exists(cloud_container, cloud_blobname):
        md5 = file_transfer.file_instance.file_resource.md5

        if md5 is None:
            additional_message = 'no md5 available to check'

        elif md5 != get_blob_md5(block_blob_service, cloud_container, cloud_blobname):
            additional_message = 'md5 does not match'

        else:
            create_file_instance(file_transfer)
            return

        error_message = "target file {filepath} already exists on {storage}, {additional_message}".format(
            filepath=cloud_filepath,
            storage=file_transfer.to_storage.name,
            additional_message=additional_message)
        raise FileAlreadyExists(error_message)

    def progress_callback(current, total):
        if (total != 0):
            file_transfer.progress = float(current) / float(total)
            file_transfer.save()

    block_blob_service.create_blob_from_path(
        cloud_container,
        cloud_blobname,
        local_filepath,
        progress_callback=progress_callback)

    blob_md5 = get_blob_md5(block_blob_service, cloud_container, cloud_blobname)
    file_md5 = file_transfer.file_instance.file_resource.md5

    #if file_md5 is not None and file_md5 != blob_md5:
    #    error_message = "md5 mismatch for {blobname} on {storage} blob md5 {blobmd5}, file md5 {filemd5}".format(
    #        blobname=cloud_blobname,
    #        storage=file_transfer.to_storage.name,
    #        blobmd5=blob_md5,
    #        filemd5=file_md5)
    #    raise DataCorruptionError(error_message)

    create_file_instance(file_transfer)


def check_file_same_local(file_resource, filepath):
    if file_resource.size != os.path.getsize(filepath):
        return False
    return True


def transfer_file_server_server_remote(file_transfer):
    """ Transfer a file from a remote server to a local server.
    
    This should be called on the to server.
    """

    local_filepath = file_transfer.get_filepath()
    remote_filepath = file_transfer.file_instance.get_filepath()

    if os.path.isfile(local_filepath):
        if check_file_same_local(file_transfer.file_instance.file_resource, local_filepath):
            create_file_instance(file_transfer)
            os.chmod(local_filepath, 0444)
            return

        error_message = "target file {filepath} already exists on {storage}, {additional_message} with different size".format(
            filepath=local_filepath,
            storage=file_transfer.to_storage.name,
            additional_message=additional_message)
        raise FileAlreadyExists(error_message)

    with paramiko.SSHClient() as client:
        client.load_system_host_keys()

        client.connect(
            file_transfer.from_storage.server_ip,
            username=file_transfer.from_storage.username)

        sftp = custom_paramiko.SFTPClient.from_transport(
            client.get_transport(), buffer_read_length=32*1024*1024)

        try:
            sftp.stat(remote_filepath)
        except IOError as e:
            if e.errno == errno.ENOENT:
                error_message = "{filepath} does not actually exist on {storage} even though a file instance with pk : {pk} exists.".format(
                    filepath=remote_filepath,
                    storage=file_transfer.file_instance.storage.name,
                    pk=file_transfer.file_instance.id)
                raise FileDoesNotExist(error_message)
            else:
                raise

        def progress_callback(current, total):
            if(total != 0):
                file_transfer.progress = float(current) / float(total)
                file_transfer.save()

        sftp.get(
            remote_filepath,
            local_filepath,
            callback=progress_callback)

    create_file_instance(file_transfer)
    os.chmod(local_filepath, 0444)


def transfer_file_server_server_local(file_transfer):
    """ Transfer a file between storages on a server.
    """

    from_filepath = file_transfer.file_instance.get_filepath()
    to_filepath = file_transfer.get_filepath()

    if not os.path.isfile(from_filepath):
        error_message = "source file {filepath} does not exist on {storage} for file instance with pk: {pk}".format(
            filepath=from_filepath,
            storage=file_transfer.file_instance.storage.name,
            pk=file_transfer.file_instance.id)
        raise FileDoesNotExist(error_message)

    if os.path.isfile(to_filepath):
        if check_file_same_local(file_transfer.file_instance.file_resource, to_filepath):
            create_file_instance(file_transfer)
            os.chmod(local_filepath, 0444)
            return

        error_message = "target file {filepath} already exists on {storage}".format(
            filepath=to_filepath,
            storage=file_transfer.to_storage.name)
        raise FileAlreadyExists(error_message)

    def progress_callback(bytes_copied, total):
        if (total != 0):
            file_transfer.progress = float(bytes_copied) / float(total)
            file_transfer.save()

    tantalus.custom_shutils.copyfile(
        from_filepath, to_filepath, progress_callback,
        length=32*1024*1024)

    create_file_instance(file_transfer)
    os.chmod(to_filepath, 0444)


def transfer_file_server_server(file_transfer):
    """ Transfer a file from a server to blob.
    
    This should be called on the to server.
    """

    if file_transfer.from_storage.server_ip == file_transfer.to_storage.server_ip:
        transfer_file_server_server_local(file_transfer)

    else:
        transfer_file_server_server_remote(file_transfer)


def _check_deployments_complete(file_transfer):
    # TODO: could use celery chaining here
    for deployment in file_transfer.deployment_set.all():
        _check_deployment_complete(deployment)


def _check_deployment_complete(deployment):
    for file_transfer in deployment.file_transfers.all():
        if file_transfer.finished and not file_transfer.success:
            deployment.errors = True
    deployment.save()

    for file_transfer in deployment.file_transfers.all():
        if not file_transfer.finished:
            return

    deployment.finished = True
    deployment.running = False
    deployment.save()


@receiver(post_save, sender=FileTransfer)
def file_transfer_saved(sender, instance, **kwargs):
    _check_deployments_complete(instance)

