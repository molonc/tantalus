from azure.storage.blob import BlockBlobService, ContainerPermissions
import datetime
import paramiko
import time
import subprocess
import sys
import os
import logging

from tantalus.models import *
from tantalus.exceptions.file_transfer_exceptions import *
import errno

logger = logging.getLogger('azure.storage')
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(name)-20s %(levelname)-5s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

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


def make_dirs(dirname):
    try:
        os.makedirs(dirname)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def check_or_update_md5(md5_check, temp_directory):
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


def _as_gb(num_bytes):
    return round(num_bytes / (1024. * 1024.), 2)


class TransferProgress(object):
    def __init__(self):
        self._start = time.time()
        self._interval = 10
        self._last_print = self._start - self._interval * 2
    def print_progress(self, current, total):
        current_time = time.time()
        if current_time < self._last_print + self._interval:
            return
        self._last_print = current_time
        elapsed = current_time - self._start
        percent = 'NA'
        if total > 0:
            percent = '{:.2f}'.format(100. * float(current) / total)
        print '{}/{} ({}%) in {}s'.format(
            _as_gb(current),
            _as_gb(total),
            percent,
            elapsed)


class AzureTransfer(object):
    """A class useful for server-blob interactions.

    Not so much blob-to-blob interactions in its present form.
    """
    def __init__(self, storage):
        self.block_blob_service = BlockBlobService(
            account_name=storage.storage_account,
            account_key=storage.credentials.storage_key)
        self.block_blob_service.MAX_BLOCK_SIZE = 64 * 1024 * 1024

    def download_from_blob(self, file_instance, to_storage):
        """ Transfer a file from blob to a server.
        
        This should be called on the from server.
        """

        cloud_filepath = file_instance.get_filepath()
        cloud_container, cloud_blobname = cloud_filepath.split('/', 1)
        assert cloud_container == file_instance.storage.get_storage_container()
        local_filepath = to_storage.get_filepath(file_instance.file_resource)

        make_dirs(os.path.dirname(local_filepath))

        if not self.block_blob_service.exists(cloud_container, cloud_blobname):
            error_message = "source file {filepath} does not exist on {storage} for file instance with pk: {pk}".format(
                filepath=cloud_filepath,
                storage=file_instance.storage.name,
                pk=file_instance.id)
            raise FileDoesNotExist(error_message)

        if os.path.isfile(local_filepath):
            error_message = "target file {filepath} already exists on {storage}".format(
                filepath=local_filepath,
                storage=to_storage.name)
            raise FileAlreadyExists(error_message)

        self.block_blob_service.get_blob_to_path(
            cloud_container,
            cloud_blobname,
            local_filepath,
            progress_callback=TransferProgress().print_progress,
            max_connections=1)

        os.chmod(local_filepath, 0444)

    def _check_file_same_blob(self, file_resource, container, blobname):
        properties = self.block_blob_service.get_blob_properties(container, blobname)
        blobsize = properties.properties.content_length
        if file_resource.size != blobsize:
            return False
        return True

    def upload_to_blob(self, file_instance, to_storage):
        """ Transfer a file from a server to blob.
        
        This should be called on the from server.
        """

        local_filepath = file_instance.get_filepath()
        cloud_filepath = to_storage.get_filepath(file_instance.file_resource)
        cloud_container, cloud_blobname = cloud_filepath.split('/', 1)
        assert cloud_container == to_storage.get_storage_container()

        if not os.path.isfile(local_filepath):
            error_message = "source file {filepath} does not exist on {storage} for file instance with pk: {pk}".format(
                filepath=local_filepath,
                storage=file_instance.storage.name,
                pk=file_instance.id)
            raise FileDoesNotExist(error_message)

        if self.block_blob_service.exists(cloud_container, cloud_blobname):
            if self._check_file_same_blob(file_instance.file_resource, cloud_container, cloud_blobname):
                return

            error_message = "target file {filepath} already exists on {storage}".format(
                filepath=cloud_filepath,
                storage=to_storage.name)
            raise FileAlreadyExists(error_message)

        self.block_blob_service.create_blob_from_path(
            cloud_container,
            cloud_blobname,
            local_filepath,
            progress_callback=TransferProgress().print_progress,
            max_connections=1,
            timeout=10*60*64)


def blob_to_blob_transfer_closure(source_account, destination_account):
    """Returns a function for transfering blobs between Azure containers.

    Note that this will *not* create new containers that don't already
    exist. This is a useful note because for development the container
    names are changed to "{container name}-test", and these "test
    containers" are unlikely to exist.
    """
    # Start BlockBlobService for source and destination accounts
    source_storage = BlockBlobService(
        account_name=source_account.storage_account,
        account_key=source_account.credentials.storage_key)
    destination_storage = BlockBlobService(
        account_name=destination_account.storage_account,
        account_key=destination_account.credentials.storage_key)

    # Get a shared access signature for the source account so that we
    # can read its private files
    shared_access_sig = (
        source_account.generate_container_shared_access_signature(
            container_name = source_account.get_storage_container(),
            permission=ContainerPermissions.READ,
            expiry=(datetime.datetime.utcnow()
                    + datetime.timedelta(hours=200)),))


    def transfer_function(source_file, _):
        """Transfer function aware of source and destination Azure storages.

        Using non-local source_storage and destination_storage. This
        isn't Python 3, so no nonlocal keyword :(
        """
        # Copypasta validation from AzureTransfer.download_from_blob
        source_filepath = source_file.get_filepath()
        source_container, blobname = cloud_filepath.split('/', 1)
        assert source_container == source_file.storage.get_storage_container()

        if not source_storage.exists(source_container, blobname):
            error_message = "source file {filepath} does not exist on {storage} for file instance with pk: {pk}".format(
                filepath=source_filepath,
                storage=source_file.storage.name,
                pk=source_file.id)
            raise FileDoesNotExist(error_message)

        # Copypasta validation from AzureTransfer.upload_to_blob
        if destination_storage.exists(destination_account.get_storage_container(), blobname):
            # Check if the file already exist. If the file does already
            # exist, don't re-transfer this file. If the file does exist
            # but has a different size, then raise an exception.

            # Size check
            destination_blob_size = destination_storage.get_blob_properties(
                container_name=destination_account.get_storage_container(),
                blob_name=blobname,)

            if source_file.size == destination_blob_size:
                # Don't retransfer
                return
            else:
                # Raise an exception and report that a blob with this
                # name already exists!
                error_message = "target filepath {filepath} already exists on {storage} but with different filesize".format(
                    filepath=cloud_filepath,
                    storage=to_storage.name)
                raise FileAlreadyExists(error_message)

        # Finally, transfer the file between the blobs
        source_sas_url = source_storage.make_blob_url(
            container_name=source_file.storage.get_storage_container(),
            blob_name=blobname,
            sas_token=shared_access_sig)

        destination_storage.copy_blob(
            container_name=destination_account.get_storage_container(),
            blob_name=blobname,
            copy_source=source_sas_url)

    # Return the transfer function
    return transfer_function


def check_file_same_local(file_resource, filepath):
    #TODO: define 'size' for folder
    if file_resource.is_folder:
        return True

    if file_resource.size != os.path.getsize(filepath):
        return False
    
    return True


def rsync_file(file_instance, to_storage):
    """ Rsync a single file from one storage to another
    """

    local_filepath = to_storage.get_filepath(file_instance.file_resource)
    remote_filepath = file_instance.get_filepath()

    if file_instance.file_resource.is_folder:
        local_filepath = local_filepath + '/'
        remote_filepath = remote_filepath + '/'

    if os.path.isfile(local_filepath):
        if check_file_same_local(file_instance.file_resource, local_filepath):
            return
        error_message = "target file {filepath} already exists on {storage} with different size".format(
            filepath=local_filepath,
            storage=to_storage.name)
        raise FileAlreadyExists(error_message)

    if file_instance.storage.server_ip == to_storage.server_ip:
        remote_location = remote_filepath
    else:
        remote_location = file_instance.storage.username + '@' + file_instance.storage.server_ip + ':' + remote_filepath

    make_dirs(os.path.dirname(local_filepath))

    subprocess_cmd = [
        'rsync',
        '--progress',
        # '--info=progress2',
        '--chmod=D555',
        '--chmod=F444',
        '--times',
        '--copy-links',
        remote_location,
        local_filepath,
    ]

    if file_instance.file_resource.is_folder:
        subprocess_cmd.insert(1, '-r')

    sys.stdout.flush()
    sys.stderr.flush()
    subprocess.check_call(subprocess_cmd, stdout=sys.stdout, stderr=sys.stderr)

    if not check_file_same_local(file_instance.file_resource, local_filepath):
        error_message = "transfer to {filepath} on {storage} failed".format(
            filepath=local_filepath,
            storage=to_storage.name)
        raise Exception(error_message)


def get_file_transfer_function(from_storage, to_storage):
    from_storage_type = from_storage.__class__.__name__
    to_storage_type = to_storage.__class__.__name__

    if from_storage_type == 'AzureBlobStorage' and to_storage_type == 'AzureBlobStorage':
        return blob_to_blob_transfer_closure(from_storage, to_storage)
    elif from_storage_type == 'ServerStorage' and to_storage_type == 'AzureBlobStorage':
        return AzureTransfer(to_storage).upload_to_blob

    elif from_storage_type == 'AzureBlobStorage' and to_storage_type == 'ServerStorage':
        return AzureTransfer(from_storage).download_from_blob

    elif from_storage_type == 'ServerStorage' and to_storage_type == 'ServerStorage':
        return rsync_file


def transfer_files(file_transfer, temp_directory):
    """ Transfer a set of files
    """

    tag_name = file_transfer.tag_name
    from_storage = file_transfer.from_storage
    to_storage = file_transfer.to_storage

    # Generate a list of files requiring transfer
    # Lock transfer to specific storage by creating
    # reserved file instances
    file_instances = []
    for dataset in AbstractDataSet.objects.filter(tags__name=tag_name):
        file_resources = dataset.get_file_resources()

        for file_resource in file_resources:
            # Check for an existing file instance at destination
            # continue without error if one exists
            destination_file_instances = file_resource.fileinstance_set.filter(storage=to_storage)
            if len(destination_file_instances) >= 1:
                continue

            # Check that the file exists on the from server
            # fail if no file exists
            source_file_instance = file_resource.fileinstance_set.filter(storage=from_storage)
            if len(source_file_instance) == 0:
                raise FileDoesNotExist(
                    'file instance for file resource {} not deployed on source storage {}'.format(
                        file_resource.filename, from_storage.name))

            file_instance = source_file_instance[0]

            existing_transfers = FileTransfer.objects.filter(
                reservedfileinstance__to_storage=to_storage,
                reservedfileinstance__file_resource=file_resource)

            existing_transfers = existing_transfers.exclude(
                reservedfileinstance__file_transfer=file_transfer)

            if existing_transfers.count() > 0:
                raise Exception('FileResource {} for dataset {} already transferring with FileTransfer {}'.format(
                    file_resource.id, dataset.id, existing_transfers[0].id))

            ReservedFileInstance.objects.get_or_create(
                to_storage=to_storage,
                file_resource=file_resource,
                file_transfer=file_transfer,
            )

            file_instances.append(file_instance)

    f_transfer = get_file_transfer_function(from_storage, to_storage)

    # Transfer all files that have reserved file instances
    # Create each file on success
    for file_instance in file_instances:
        print 'starting transfer of {} to {}'.format(file_instance.file_resource.filename, to_storage.name)
        f_transfer(file_instance, to_storage)
        FileInstance.objects.create(file_resource=file_instance.file_resource, storage=to_storage)
        print 'finished transfer of {} to {}'.format(file_instance.file_resource.filename, to_storage.name)
