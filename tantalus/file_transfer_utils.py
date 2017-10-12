from azure.storage.blob import BlockBlobService
import paramiko
import os, io
import hashlib
from tantalus.models import *
from tantalus.exceptions.file_transfer_exceptions import *
import errno


# if available memory on the storage is less than this, include this as a possible source of error if the transfer fails
__MINIMUM_FREE_DISK_SPACE = 50e10


def check_file_exists_on_cloud(service, storage, file_transfer):
    """
    Raises exception if file does not actually exist, and (deletes file instance object?)
    :param service: blob storage service client
    :param storage: storage instance
    :param file_transfer: file transfer instance
    :return: raises FileDoesNotActuallyExist exception
    """
    filename = file_transfer.file_instance.file_resource.filename.strip("/")
    if not service.exists(storage.storage_container, filename):
        # TODO: delete file instance object?
        error_message = "{filename} does not actually exist on {storage} even though a file instance with pk : {pk} exists.".format(
            filename = filename,
            storage = storage.name,
            pk = file_transfer.file_instance_id)
        update_file_transfer(file_transfer, success=False, error_message=error_message)
        raise FileDoesNotActuallyExist(error_message)


def check_file_exists_on_server(storage, file_transfer):
    """
    Raises exception if file does not actually exist, and (deletes file instance object?)
    :param storage:
    :param file_transfer:
    :return: raises FileDoesNotActuallyExist exception
    """
    filename = file_transfer.file_instance.file_resource.filename
    filepath = os.path.join(storage.storage_directory, filename.strip('/'))
    if not os.path.isfile(filepath):
        # TODO: delete file instance object?
        error_message = "{filepath} does not actually exist on {storage} even though a file instance with pk : {pk} exists.".format(
                filepath=filepath,
                storage=storage.name,
                pk=file_transfer.file_instance_id)
        update_file_transfer(file_transfer, success=False, error_message=error_message)
        raise FileDoesNotActuallyExist(error_message)


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


def check_data_corruption(md5, file_transfer):
    """
    Checks for data corruption through md5 comparison.
    Updates FileTransfer object with error message and throws DataCorruptionError if md5s do not match

    :param md5: 32 character hexadecimal md5 string OR 24 character base64 md5 string if base_64_encoding==true
    :param file_transfer: file transfer object
    :return:
    """

    try:
        # if md5 sums match, create the file instance
        check_md5(md5, file_transfer)
        create_file_instance(file_transfer)

        # updating the status of the file transfer to a completed state, successful transfer
        update_file_transfer(file_transfer, success=True)
    except DataCorruptionError as e:
        # updating the status of the file transfer to a completed state, failed transfer
        update_file_transfer(
                file_transfer,
                success=False,
                error_message=e.message
        )
        # TODO move this update of file transfer to tasks
        raise DataCorruptionError(e.message)


def check_data_corruption_with_base_64_md5(md5, file_transfer):
    """
    Checks for data corruption through md5 comparison.
    Updates FileTransfer object with error message and throws DataCorruptionError if md5s do not match

    :param md5: 24 character base64 md5 string if base_64_encoding==true or None
    :param file_transfer: file transfer object
    :return:
    """

    # for empty files, the base_64_md5 returned by azure is None, so skip comparing md5s for these files
    if md5 is None:
        if file_transfer.file_instance.file_resource.size == 0:
            create_file_instance(file_transfer)
            update_file_transfer(file_transfer, success=True)
        else:
            update_file_transfer(file_transfer, success=True,
                                 error_message="Null MD5 hash for file but file should not be size 0")
            raise DataCorruptionError()
    else:
        # convert the base_64_md5 to hexadecimal encoded md5 to compare with database md5s
        md5 = md5.decode("base64").encode("hex")
        check_data_corruption(md5, file_transfer)


def update_file_transfer(file_transfer, success=False, error_message=""):
    """
    updates the file transfer object to a completed state, indicates success status
    :param file_transfer: FileTransfer object
    :param success: Boolean value, indicating whether transfer was successful
    :param error_message: the error message, if any
    :return:
    """
    file_transfer.running = False
    file_transfer.finished = True
    file_transfer.success = success
    file_transfer.error_messages = error_message
    file_transfer.save()


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


def perform_create_subdirectories(file_transfer):
    filepath = os.path.join(str(file_transfer.to_storage.storage_directory), file_transfer.new_filename.strip('/'))
    dirname = os.path.dirname(filepath)
    error = False
    try:
        os.makedirs(dirname)
    except Exception as e:
        error = True
        error_message = str(e)
    if error:
        print error_message
    os.system('ls ' + dirname)


def perform_transfer_file_azure_server(file_transfer):
    block_blob_service = get_block_blob_service(storage=file_transfer.from_storage)
    check_file_exists_on_cloud(block_blob_service, file_transfer.from_storage, file_transfer)

    def progress_callback(current, total):
        if total != 0:
            file_transfer.progress = float(current) / float(total)
            file_transfer.save()

    cloud_filename = file_transfer.file_instance.file_resource.filename.strip("/") # TODO: throw error? path/name of blob

    # make subdirectories for file if they don't exist
    #TODO: refactor this into helper?
    filepath = os.path.join(str(file_transfer.to_storage.storage_directory), file_transfer.new_filename.strip('/'))

    try:
        block_blob_service.get_blob_to_path(
            file_transfer.from_storage.storage_container,
            cloud_filename, #TODO: throw error? path/name of blob
            filepath, #path/name of file
            progress_callback=progress_callback)

    except Exception as e:
        update_file_transfer(file_transfer, success=False, error_message=str(e))
        raise

    base_64_md5 = block_blob_service.get_blob_properties(
        file_transfer.from_storage.storage_container,
        cloud_filename).properties.content_settings.content_md5
    check_data_corruption_with_base_64_md5(base_64_md5, file_transfer)

    # TODO: propagate errors to tasks and raise them to form json response with error code after updating file transfer object



def perform_transfer_file_server_azure(file_transfer):
    block_blob_service = get_block_blob_service(storage=file_transfer.to_storage)
    check_file_exists_on_server(file_transfer.from_storage, file_transfer)

    def progress_callback(current, total):
        if (total != 0):
            file_transfer.progress = float(current) / float(total)
            file_transfer.save()

    # uploading file to test cloud storage, remember to strip the slash! Otherwise this creates an additional
    # <no name> root folder
    cloud_filepath = file_transfer.new_filename.strip('/')
    local_filepath = os.path.join(file_transfer.from_storage.storage_directory, file_transfer.file_instance.file_resource.filename.strip('/'))

    try:
        block_blob_service.create_blob_from_path(
            file_transfer.to_storage.storage_container,
            cloud_filepath, #path/name of blob
            local_filepath, #path/name of file
            progress_callback=progress_callback)

    except Exception as e:
        print str(e)
        update_file_transfer(file_transfer, success=False, error_message=str(e))
        raise

    base_64_md5 = block_blob_service.get_blob_properties(file_transfer.to_storage.storage_container, cloud_filepath).properties.content_settings.content_md5
    #TODO: add tests for this
    check_data_corruption_with_base_64_md5(base_64_md5, file_transfer)



def perform_transfer_file_server_server(file_transfer):
    # check that file exists on local server
    check_file_exists_on_server(file_transfer.from_storage, file_transfer)

    # setting up SSHClient
    client = paramiko.SSHClient()
    client.load_system_host_keys()

    client.connect(
        file_transfer.to_storage.server_ip,
        username=file_transfer.to_storage.username)

    sftp = paramiko.SFTPClient.from_transport(client.get_transport())

    def progress_callback(current, total):
        if(total!=0):
            file_transfer.progress = float(current) / float(total)
            file_transfer.save()

    # TODO: refactor this into helper?
    # creating subdirectories for remote path if they don't exist
    local_filepath = os.path.join(file_transfer.from_storage.storage_directory, file_transfer.file_instance.file_resource.filename.strip('/'))
    remote_filepath = os.path.join(file_transfer.to_storage.storage_directory, file_transfer.new_filename.strip('/'))

    # put file into remote server
    try:
        sftp.put(
            local_filepath,  # absolute path
            remote_filepath, # absolute path of file in the remote server
            callback=progress_callback)

    except EnvironmentError as e: # IOError and OSError exceptions are caught here
        # TODO: add other errors where we would simply pop off file transfer again
        if e.errno == errno.EPIPE: # Error code 32 - broken pipe
            update_file_transfer(file_transfer, success=False, error_message=e.strerror)
            raise RecoverableFileTransferError(e.strerror)
            # TODO: make the celery work try the file transfer again

        elif e.message == 'Failure': # SFTP code 4 failure - An error occurred, but no specific error code exists to describe the failure
            #  warning: ensure that any failures with checks don't overwrite actual exceptions

            e.message = e.message + " - No specific error code was given.\nPossible reasons include:"

            # check uploading a file to a full filesystem
            cmd = "df " + file_transfer.to_storage.storage_directory
            stdin, stdout, stderr = client.exec_command(cmd)
            stdout.channel.recv_exit_status() # This is a blocking call to wait for output
            available_space = stdout.readlines()[1].split()[3] # parse out available space from output

            if float(available_space) < __MINIMUM_FREE_DISK_SPACE:
                e.message = e.message + "\n- A file is being uploaded to a full filesystem - available disk space is {} kilobytes".format(available_space)
                print e.message

            update_file_transfer(file_transfer, success=False, error_message=e.message)
            raise

    except Exception as e:
        update_file_transfer(file_transfer, success=False, error_message=str(e))
        print str(e)
        raise

    # retrieve transferred file object
    # b flag for binary is not needed because SSH treats all files as binary
    transferred_file = sftp.file(remote_filepath, mode='r')
    md5 = get_md5(transferred_file)
    #TODO: add tests for this
    check_data_corruption(md5, file_transfer)

    transferred_file.close()
    client.close()