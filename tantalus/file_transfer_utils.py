from azure.storage.blob import BlockBlobService
import paramiko
import os, io
import hashlib
import subprocess
from tantalus.models import *
from tantalus.exceptions.file_transfer_exceptions import *
import errno


# if available memory on the storage is less than this, include this as a possible source of error if the transfer fails
__MINIMUM_FREE_DISK_SPACE = 50e10


def get_md5(f, chunk_size=134217728):
    """
    get the md5 string of a given file OBJECT, not path

    :param f: file OBJECT, not path this is to work with the SFTPFile object
    :param chunk_size: size of the buffer
    :return: md5 string (32 chars)
    """
    hash_md5 = hashlib.md5()
    for chunk in iter(lambda: f.read(chunk_size), b""):
        hash_md5.update(chunk)
    md5 =  hash_md5.hexdigest()
    return md5


def check_md5(md5, file_transfer):
    database_saved_md5 = file_transfer.file_instance.file_resource.md5
    if (md5 != database_saved_md5):
        error_message = "Data has been corrupted - file md5 is {} while database md5 is {}".format(md5, database_saved_md5)
        print error_message
        raise DataCorruptionError(error_message)


class MD5CheckError(Exception):
    pass


def check_or_update_md5(md5_check):
    """ Check or update an md5 for a file instance in an md5 check object.
    """

    filepath = md5_check.file_instance.get_filepath()

    try:
        md5 = subprocess.check_output(['md5sum', filepath]).split()[0]
    except Exception as e:
        raise MD5CheckError('Unable to run md5sum on {}\n{}'.format(filepath, str(e)))

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
        account_key=storage.storage_key)
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
    local_filepath = file_transfer.get_filepath()

    if not service.exists(file_transfer.file_instance.storage.storage_container, cloud_filepath):
        error_message = "source file {filepath} does not exist on {storage} for file instance with pk: {pk}".format(
            filepath=cloud_filepath,
            storage=file_transfer.file_instance.storage.name,
            pk=file_transfer.file_instance.id)
        raise FileDoesNotExist(error_message)

    if os.path.isfile(local_filepath):
        error_message = "target file {filepath} already exists on {storage}".format(
            filepath=local_filepath,
            storage=file_instance.storage.name)
        raise FileAlreadyExists(error_message)

    def progress_callback(current, total):
        if total != 0:
            file_transfer.progress = float(current) / float(total)
            file_transfer.save()

    block_blob_service.get_blob_to_path(
        file_transfer.file_instance.storage.storage_container,
        cloud_filepath,
        local_filepath,
        progress_callback=progress_callback)

    create_file_instance(file_transfer)

    _check_deployments_complete(file_transfer)


def transfer_file_server_azure(file_transfer):
    """ Transfer a file from a server to blob.
    
    This should be called on the from server.
    """

    block_blob_service = get_block_blob_service(storage=file_transfer.to_storage)

    local_filepath = file_transfer.file_instance.get_filepath()
    cloud_filepath = file_transfer.get_filepath()

    if not os.path.isfile(local_filepath):
        error_message = "source file {filepath} does not exist on {storage} for file instance with pk: {pk}".format(
            filepath=local_filepath,
            storage=file_transfer.file_instance.storage.name,
            pk=file_transfer.file_instance.id)
        raise FileDoesNotExist(error_message)

    if service.exists(file_transfer.file_instance.storage.storage_container, cloud_filepath):
        error_message = "target file {filepath} already exists on {storage}".format(
            filepath=cloud_filepath,
            storage=file_instance.storage.name)
        raise FileAlreadyExists(error_message)

    def progress_callback(current, total):
        if (total != 0):
            file_transfer.progress = float(current) / float(total)
            file_transfer.save()

    block_blob_service.create_blob_from_path(
        file_transfer.to_storage.storage_container,
        cloud_filepath,
        local_filepath,
        progress_callback=progress_callback)

    base_64_md5 = block_blob_service.get_blob_properties(
        file_transfer.from_storage.storage_container,
        cloud_filepath).properties.content_settings.content_md5
    md5 = base_64_md5.decode("base64").encode("hex")

    file_resource_md5 = file_transfer.file_instance.file_resource.md5

    if file_resource_md5 is not None and file_resource_md5 != md5:
        error_message = "Data corruption: cloud md5 {}, file md5 {}".format(md5, file_resource_md5)
        raise DataCorruptionError(error_message)

    create_file_instance(file_transfer)

    _check_deployments_complete(file_transfer)


def transfer_file_server_server(file_transfer):
    """ Transfer a file from a server to blob.
    
    This should be called on the to server.
    """

    client = paramiko.SSHClient()
    client.load_system_host_keys()

    client.connect(
        file_transfer.from_storage.server_ip,
        username=file_transfer.from_storage.username)

    sftp = paramiko.SFTPClient.from_transport(client.get_transport())

    local_filepath = file_transfer.get_filepath()
    remote_filepath = file_transfer.file_instance.get_filepath()

    if os.path.isfile(local_filepath):
        error_message = "target file {filepath} already exists on {storage}".format(
            filepath=local_filepath,
            storage=file_transfer.to_storage.name)
        raise FileAlreadyExists(error_message)

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

    try:
        sftp.get(
            remote_filepath,
            local_filepath,
            callback=progress_callback)

    except EnvironmentError as e: # IOError and OSError exceptions are caught here
        # TODO: add other errors where we would simply pop off file transfer again
        if e.errno == errno.EPIPE: # Error code 32 - broken pipe
            raise RecoverableFileTransferError(e.strerror)
            # TODO: make the celery work try the file transfer again

        elif e.message == 'Failure': # SFTP code 4 failure - An error occurred, but no specific error code exists to describe the failure
            #  warning: ensure that any failures with checks don't overwrite actual exceptions

            e.message = e.message + " - No specific error code was given.\nPossible reasons include:"

            # check uploading a file to a full filesystem
            # cmd = "df " + file_transfer.to_storage.storage_directory
            # stdin, stdout, stderr = client.exec_command(cmd)
            # stdout.channel.recv_exit_status() # This is a blocking call to wait for output
            # available_space = stdout.readlines()[1].split()[3] # parse out available space from output
            # 
            # if float(available_space) < __MINIMUM_FREE_DISK_SPACE:
            #     e.message = e.message + "\n- A file is being uploaded to a full filesystem - available disk space is {} kilobytes".format(available_space)

            raise

    client.close()

    create_file_instance(file_transfer)

    _check_deployments_complete(file_transfer)


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
    deployment.save()


