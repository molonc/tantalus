from azure.storage.blob import BlockBlobService
import paramiko
import os

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

    block_blob_service.get_blob_to_path(
        file_transfer.from_storage.storage_container,
        file_transfer.file_instance.filename.strip("/"), #TODO: throw error? path/name of blob
        file_transfer.new_filename, #path/name of file
        progress_callback=progress_callback)


def perform_transfer_file_server_azure(file_transfer):
    block_blob_service = get_block_blob_service(storage=file_transfer.to_storage)

    def progress_callback(current, total):
        if (total != 0):
            file_transfer.progress = float(current) / float(total)
            file_transfer.save()

    block_blob_service.create_blob_from_path(
        file_transfer.to_storage.storage_container,
        file_transfer.new_filename.strip("/"), #path/name of blob
        file_transfer.file_instance.filename, #path/name of file
        progress_callback=progress_callback)


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

    sftp.put(
        file_transfer.file_instance.filename,  # absolute path
        os.path.join(file_transfer.to_storage.storage_directory, file_transfer.new_filename),
        callback=progress_callback)

    client.close()