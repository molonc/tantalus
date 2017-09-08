import os, sys, subprocess
import paramiko, requests
import django
from django.test import TestCase

from tantalus.models import *
from misc.update_tantalus_db import *
import socket
from tantalus.file_transfer_utils import *
from django.utils import timezone


## TEST CONSTANTS ##
COMPUTE2_TEST_DIRECTORY = "/home/jngo/tantalus-test/"
COMPUTE2_IP = "10.9.2.187"

BEAST_TEST_DIRECTORY = "/home/jngo/tantalus-test/"
BEAST_IP = "10.9.4.26"

ROCKS_TEST_DIRECTORY = "/home/jngo/tantalus-test/"
ROCKS_IP = "10.9.4.27"

AZURE_STORAGE_ACCOUNT = "singlecellstorage"
AZURE_STORAGE_CONTAINER = "jess-testing"
AZURE_STORAGE_KEY = "okQAsp72BagVWpGLEaUNO30jH9XGLuVj3EDmbtg7oV6nmH7+9E+4csF+AXn4G3YMEKebnCnsRwVu9fRhh2RiMQ=="

LOCAL_TEST_DIRECTORY = "/Users/jngo/test-file-transfer/"
LOCAL_IP = "momac31.bccrc.ca"

# Use with the _add_test_files function to create multiple files
BASE_FILENAME = "test_file"
NEW_FILENAME = "new_test_file"

#these are all dummy values for the files to be created
FILE_MD5 = 0 # iterated by 1 to create a unique md5 for each test file
FILE_SIZE = "20"
FILE_CREATION_DATE = timezone.now()
FILE_TYPE= SequenceDataFile.FQ
FILE_COMPRESSION = SequenceDataFile.UNCOMPRESSED


USER="jngo"
PASSWORD="MySecurePassword!"


## HELPER TEST FUNCTIONS ##
def connect_sftp_server(server_ip, username):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.connect(
        server_ip,
        username=username)
    sftp = paramiko.SFTPClient.from_transport(client.get_transport())
    return client, sftp


def _clear_test_cloud_storage(blob_storage):
    service = get_block_blob_service(blob_storage)
    for blob in service.list_blobs(blob_storage.storage_container):
        service.delete_blob(blob_storage.storage_container, blob.name)


def _add_storages():

    rocks = ServerStorage(
        name = 'rocks',
        server_ip = ROCKS_IP,
        storage_directory = ROCKS_TEST_DIRECTORY,
        username = USER,
    )
    rocks.full_clean()
    rocks.save()

    blob_storage = AzureBlobStorage(
        name = 'azure_sc_fastqs',
        storage_account = AZURE_STORAGE_ACCOUNT,
        storage_container = AZURE_STORAGE_CONTAINER,
        storage_key = AZURE_STORAGE_KEY,
    )
    blob_storage.full_clean()
    blob_storage.save()
    _clear_test_cloud_storage(blob_storage)

    compute2 = ServerStorage(
        name='compute2',
        server_ip=COMPUTE2_IP,
        storage_directory=BEAST_TEST_DIRECTORY,
        username=USER,
    )
    compute2.full_clean()
    compute2.save()

    beast = ServerStorage(
        name = 'beast',
        server_ip = BEAST_IP,
        storage_directory = BEAST_TEST_DIRECTORY,
        username = USER,
    )
    beast.full_clean()
    beast.save()

    local = ServerStorage(
        name = 'jngo',
        server_ip=LOCAL_IP,
        storage_directory = LOCAL_TEST_DIRECTORY,
        username=USER,
    )
    local.full_clean()
    local.save()

    storages = {
        'rocks':rocks,
        'blob_storage':blob_storage,
        'compute2':compute2,
        'beast':beast,
        'local':local
    }

    return storages


def _create_file_resource(count):
    for i in range (0, count):
        md5 = str(FILE_MD5 + i)

        test_seqfile = SequenceDataFile(
            md5 = md5,
            size = FILE_SIZE,
            created = FILE_CREATION_DATE,
            file_type = FILE_TYPE,
            compression = FILE_COMPRESSION
        )
        test_seqfile.save()


def _add_file_instances_to_server(storage, file_resource, filename, dnasequence):
    serverfile = FileInstance(
        storage = storage,
        file_resource = file_resource,
        filename = filename,
    )
    serverfile.save()

    hostname = socket.gethostname()
    cmd = "touch " + os.path.join(storage.storage_directory, filename)
    if (hostname == storage.server_ip):
        subprocess.call(cmd, shell=True)
    else:
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.connect(storage.server_ip)
        client.exec_command(cmd)
        client.close()

    fastq_files = SingleEndFastqFile(
        reads_file = file_resource,
        dna_sequences=dnasequence,
    )
    fastq_files.save()

    fastq_files.lanes = [SequenceLane.objects.get(id=1)]
    fastq_files.sequence_data.add(file_resource)
    fastq_files.save()

def _add_file_instances_to_cloud(storage, file_resource, filename, dnasequence):
    serverfile = FileInstance(
        storage=storage,
        file_resource=file_resource,
        filename=filename,
    )
    serverfile.save()

    # creating singleendfastq object with no m2m relationships
    fastq_files = SingleEndFastqFile(
        reads_file=file_resource,
        dna_sequences=dnasequence,
    )
    fastq_files.save()

    # separating assignment of m2m relationships because object needs to exist first
    fastq_files.lanes = [SequenceLane.objects.all()[0]]
    fastq_files.sequence_data.add(file_resource)
    fastq_files.save()

## TESTS ##

class FileTransferTest(TestCase):
    storage_servers = {}

    @classmethod
    def setUpTestData(cls):
        add_new_samples(['SA928'])
        add_new_libraries(['A90652A'])
        add_new_sequencelanes(['CB95TANXX_6'])

        cls.storage_servers = _add_storages()


    def test_file_transfer_server_server(self):
        from_storage = self.storage_servers['local']
        to_storage = self.storage_servers['rocks']
        filename = os.path.join(from_storage.storage_directory, BASE_FILENAME)
        _create_file_resource(count=1)

        client, sftp = connect_sftp_server(to_storage.server_ip, to_storage.username)
        self.assertRaises(IOError, sftp.stat, filename)
        client.close()

        _add_file_instances_to_server(
            storage = from_storage,
            file_resource = SequenceDataFile.objects.all()[0],
            filename = filename,
            dnasequence = DNASequences.objects.all()[0]
        )

        new_test_file = os.path.join(to_storage.storage_directory + "new_test_file")
        file_transfer = FileTransfer(
            from_storage = from_storage,
            to_storage = to_storage,
            file_instance = FileInstance.objects.all()[0],
            new_filename = new_test_file,
        )

        # self.assertRaises(IOError, sftp.stat, filename)
        client, sftp = connect_sftp_server(to_storage.server_ip, to_storage.username)

        perform_transfer_file_server_server(file_transfer = file_transfer)

        try:
            sftp.stat(new_test_file)
        except:
            self.fail("Test for file transfer failed - {} was not found".format(new_test_file))

        sftp.remove(new_test_file)
        client.close()


    def test_file_transfer_server_azure(self):
        from_storage = self.storage_servers['local']
        to_storage = self.storage_servers['blob_storage']
        service = get_block_blob_service(to_storage)
        filename = os.path.join(from_storage.storage_directory, BASE_FILENAME)
        _create_file_resource(count=1)
        _clear_test_cloud_storage(to_storage)

        for blob in service.list_blobs(to_storage.storage_container):
            if blob.name == filename:
                self.fail()

        _add_file_instances_to_server(
            storage = from_storage,
            file_resource = SequenceDataFile.objects.all()[0],
            filename = filename,
            dnasequence = DNASequences.objects.all()[0],
        )

        # this should reflect folder structure on cloud blob storage
        # when performing the file transfer, the root "/" should be stripped, otherwise it creates a
        # <no name> folder at the root of the cloud storage to act as the "root" folder
        new_test_file = os.path.join("/testing/folder/depth/", "new_test_file").strip("/")
        file_transfer = FileTransfer(
            from_storage = from_storage,
            to_storage = to_storage,
            file_instance = FileInstance.objects.all()[0],
            new_filename = new_test_file,
        )

        perform_transfer_file_server_azure(file_transfer)

        # remember to strip the root "/" in tests, because we stripped this when transferring to the cloud
        self.assertTrue(new_test_file.strip("/") in [blob.name
                                          for blob in service.list_blobs(to_storage.storage_container)])


    def test_file_transfer_azure_server(self):
        from_storage = self.storage_servers['blob_storage']
        to_storage = self.storage_servers['local']
        service = get_block_blob_service(from_storage)
        local_filename = os.path.join(to_storage.storage_directory, BASE_FILENAME)
        cloud_filename = "/testing2/folder2/depth2/TESTING-CLOUD-FILE"
        _create_file_resource(count=1)
        _clear_test_cloud_storage(from_storage)

        # removing test file from previous tests
        os.remove(local_filename)
        self.assertFalse(os.path.isfile(local_filename))

        # creating file to populate test cloud storage
        cmd = "touch " + os.path.join(local_filename)
        subprocess.call(cmd, shell=True)
        self.assertTrue(os.path.isfile(local_filename))

        # uploading file to test cloud storage, remember to strip the slash! Otherwise this creates an additional
        # <no name> root folder
        service.create_blob_from_path(
            from_storage.storage_container,  # name of container
            cloud_filename.strip("/"),  # name of the blob
            local_filename)

        # deleting file used to populate the test cloud storage
        os.remove(local_filename)
        self.assertFalse(os.path.isfile(local_filename))

        # creating file instance object and related file type object for the file on the test cloud storage
        _add_file_instances_to_cloud(
            storage = from_storage,
            file_resource = SequenceDataFile.objects.all()[0],
            filename = cloud_filename,
            dnasequence = DNASequences.objects.all()[0],
        )

        # creating file transfer object for test
        file_transfer = FileTransfer(
            from_storage=from_storage,
            to_storage=to_storage,
            file_instance=FileInstance.objects.all()[0],
            new_filename=local_filename,
        )

        # check if file exists after transfer
        perform_transfer_file_azure_server(file_transfer=file_transfer)
        self.assertTrue(os.path.isfile(local_filename))