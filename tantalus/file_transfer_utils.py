from azure.storage.blob import BlockBlobService
import paramiko
import os, io
import hashlib
from tantalus.models import *

class DataCorruptionError(Exception):
    """ Raised when MD5 calculated does not match the saved database md5 for the file resource """

def get_md5(f, chunk_size=134217728):
    """ this function uses a file object, not the path - this is to work with the SFTPFile object"""
    hash_md5 = hashlib.md5()
    for chunk in iter(lambda: f.read(chunk_size), b""):
        hash_md5.update(chunk)
    md5 =  hash_md5.hexdigest()
    return md5


def check_md5(md5, file_transfer):
    database_saved_md5 = file_transfer.file_instance.file_resource.md5
    if (md5 != database_saved_md5):
        raise DataCorruptionError


def update_file_transfer(file_transfer, success=False):
    file_transfer.running = False
    file_transfer.finished = True
    file_transfer.success = success
    file_transfer.save()


def create_file_instance(file_transfer):
    file_instance = FileInstance(
        storage=file_transfer.to_storage,
        file_resource=file_transfer.file_instance.file_resource,
        filename=file_transfer.new_filename)
    file_instance.save()


def get_block_blob_service(storage):
    block_blob_service = BlockBlobService(
        account_name=storage.storage_account,
        account_key=storage.storage_key)
    return block_blob_service

def perform_transfer_file_azure_server(file_transfer):
    block_blob_service = get_block_blob_service(storage=file_transfer.from_storage)

    def progress_callback(current, total):
        if (total != 0):
            file_transfer.progress = float(current) / float(total)
            file_transfer.save()

    cloud_filename = file_transfer.file_instance.filename.strip("/") #TODO: throw error? path/name of blob

    block_blob_service.get_blob_to_path(
        file_transfer.from_storage.storage_container,
        cloud_filename, #TODO: throw error? path/name of blob
        file_transfer.new_filename, #path/name of file
        progress_callback=progress_callback)

    md5 = block_blob_service.get_blob_properties(file_transfer.from_storage.storage_container, cloud_filename).properties.content_settings.content_md5
    try:
        #for empty files, the md5 returned is None, so don't compare md5s for these files since they dont use the null hash
        if md5!=None and os.path.getsize(file_transfer.file_instance.filename)!=0:
            check_md5(md5, file_transfer)
        create_file_instance(file_transfer)
        # updating the status of the file transfer to a completed state, successful transfer
        update_file_transfer(file_transfer, success=True)

    except DataCorruptionError:
        # updating the status of the file transfer to a completed state, failed transfer
        update_file_transfer(file_transfer, success=False)



def perform_transfer_file_server_azure(file_transfer):
    block_blob_service = get_block_blob_service(storage=file_transfer.to_storage)

    def progress_callback(current, total):
        if (total != 0):
            file_transfer.progress = float(current) / float(total)
            file_transfer.save()

    # uploading file to test cloud storage, remember to strip the slash! Otherwise this creates an additional
    # <no name> root folder
    cloud_filename = file_transfer.new_filename.strip("/")
    block_blob_service.create_blob_from_path(
        file_transfer.to_storage.storage_container,
        cloud_filename, #path/name of blob
        file_transfer.file_instance.filename, #path/name of file
        progress_callback=progress_callback)

    md5 = block_blob_service.get_blob_properties(file_transfer.to_storage.storage_container, cloud_filename).properties.content_settings.content_md5

    try:
        #for empty files, the md5 returned is None, so don't compare md5s for these files since they dont use the null hash
        if md5!=None and os.path.getsize(file_transfer.file_instance.filename)!=0:
            check_md5(md5, file_transfer)

        create_file_instance(file_transfer)
        # updating the status of the file transfer to a completed state, successful transfer
        update_file_transfer(file_transfer, success=True)

    except DataCorruptionError:
        # updating the status of the file transfer to a completed state, failed transfer
        update_file_transfer(file_transfer, success=False)


def perform_transfer_file_server_server(file_transfer):
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

    new_filename = os.path.join(file_transfer.to_storage.storage_directory, file_transfer.new_filename)

    sftp.put(
        file_transfer.file_instance.filename,  # absolute path
        new_filename, # absolute path of file in the remote server
        callback=progress_callback)

    transferred_file = sftp.file(new_filename, mode='r')
    # b flag for binary is not needed because SSH treats all files as binary
    md5 = get_md5(transferred_file)

    try:
        # if md5 sums match, create the file instance
        check_md5(md5, file_transfer)
        create_file_instance(file_transfer)

        # updating the status of the file transfer to a completed state, successful transfer
        update_file_transfer(file_transfer, success=True)
    except DataCorruptionError:
        # updating the status of the file transfer to a completed state, failed transfer
        update_file_transfer(file_transfer, success=False)

    transferred_file.close()
    client.close()