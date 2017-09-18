import os, sys, subprocess
import paramiko, requests
import django
from django.test import TestCase

from tantalus.models import *
from misc.update_tantalus_db import *
import socket, getpass
from tantalus.file_transfer_utils import *
from django.utils import timezone
import shutil

ROCKS_USER = 'jngo'

## TEST CONSTANTS ##

# !!!! NOTE - NEVER PUT ANYTHING IMPORTANT IN THE TEST DIRECTORIES - THEY WILL BE WIPED AFTER EVERY TEST !!!!
COMPUTE2_TEST_DIRECTORY = "/home/{}/tantalus-test/".format(ROCKS_USER)
COMPUTE2_IP = "10.9.2.187"

BEAST_TEST_DIRECTORY = "/home/{}/tantalus-test/".format(ROCKS_USER)
BEAST_IP = "10.9.4.26"

ROCKS_TEST_DIRECTORY = "/home/{}/tantalus-test/".format(ROCKS_USER)
ROCKS_IP = "10.9.4.27"

AZURE_STORAGE_ACCOUNT = "singlecellstorage"
AZURE_STORAGE_CONTAINER = "jess-testing"
AZURE_STORAGE_KEY = "okQAsp72BagVWpGLEaUNO30jH9XGLuVj3EDmbtg7oV6nmH7+9E+4csF+AXn4G3YMEKebnCnsRwVu9fRhh2RiMQ=="

LOCAL_USER = getpass.getuser()
LOCAL_TEST_DIRECTORY = os.path.join(os.path.realpath(os.path.dirname(__file__)),
                                    "test-file-destination-directory")
# LOCAL_TEST_DIRECTORY = "/Users/jngo/cloud-test-file-transfer"
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
LOCAL_IP = s.getsockname()[0]
s.close()

# Test directory that contains test file to populate cloud for cloud - server transfer
DIR_TO_POPULATE_CLOUD = os.path.join(os.path.realpath(os.path.dirname(__file__)),
                                    "test-file-source-directory")
FILE_TO_POPULATE_CLOUD = "cloud-test-file"

# Use with the _add_test_files function to create multiple files
BASE_FILENAME = "testing/sub/directories/test_file"
NEW_FILENAME = "new_test_file"

#these are all dummy values for the files to be created
FILE_MD5 = 0 # iterated by 1 to create a unique md5 for each test file
FILE_SIZE = "20"
FILE_CREATION_DATE = timezone.now()
FILE_TYPE= SequenceDataFile.FQ
FILE_COMPRESSION = SequenceDataFile.UNCOMPRESSED


## HELPER TEST FUNCTIONS ##
def connect_sftp_server(server_ip, username):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.connect(
        server_ip,
        username=username)
    sftp = paramiko.SFTPClient.from_transport(client.get_transport())
    return client, sftp


def _clear_up_test_files(directory_to_clean):
    if os.path.isdir(directory_to_clean):
        shutil.rmtree(directory_to_clean)

def _clear_test_cloud_storage(blob_storage):
    service = get_block_blob_service(blob_storage)
    for blob in service.list_blobs(blob_storage.storage_container):
        service.delete_blob(blob_storage.storage_container, blob.name)


def _add_storages():

    rocks = ServerStorage(
        name = 'rocks',
        server_ip = ROCKS_IP,
        storage_directory = ROCKS_TEST_DIRECTORY,
        username = ROCKS_USER,
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
        username=ROCKS_USER,
    )
    compute2.full_clean()
    compute2.save()

    beast = ServerStorage(
        name = 'beast',
        server_ip = BEAST_IP,
        storage_directory = BEAST_TEST_DIRECTORY,
        username = ROCKS_USER,
    )
    beast.full_clean()
    beast.save()

    local = ServerStorage(
        name = 'jngo',
        server_ip=LOCAL_IP,
        storage_directory = LOCAL_TEST_DIRECTORY,
        username=ROCKS_USER,
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
            compression = FILE_COMPRESSION,
            filename = BASE_FILENAME + "_" + str(i)
        )
        test_seqfile.save()


def _add_file_instances_to_server(storage, file_resource, dnasequence, create=True):
    """
    Adds the file instance for the given file resource, and a SingleEndFastq instance to represent the file
    Has a create flag to determine whether or not the files are actually created on the servers

    :param storage:
    :param file_resource:
    :param dnasequence:
    :param create: if create is true, the files on the server will also be created,
    this is used to test the FileDoesNotActuallyExist exception - defaults to true otherwise
    :return:
    """
    serverfile = FileInstance(
        storage = storage,
        file_resource = file_resource,
    )
    serverfile.save()

    # creating files on the server
    if create:
        filepath = os.path.join(str(storage.storage_directory), serverfile.file_resource.filename)
        dirname, filename = os.path.split(filepath.rstrip('/'))
        cmd1 = "mkdir -p " + dirname
        cmd2 = "chmod -R 777 " + dirname
        cmd3 = "touch " + filepath
        if (LOCAL_IP == storage.server_ip):
            subprocess.call(cmd1, shell=True)
            subprocess.call(cmd2, shell=True)
            subprocess.call(cmd3, shell=True)

        else:
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.connect(storage.server_ip)
            client.exec_command(cmd1)
            client.exec_command(cmd2)
            client.exec_command(cmd3)
            client.close()

    fastq_files = SingleEndFastqFile(
        reads_file = file_resource,
        dna_sequences=dnasequence,
    )
    fastq_files.save()

    fastq_files.lanes = [SequenceLane.objects.get(id=1)]
    fastq_files.save()

def _add_file_instances_to_cloud(storage, file_resource, dnasequence):
    serverfile = FileInstance(
        storage=storage,
        file_resource=file_resource,
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


    def setUp(self):
        _clear_up_test_files(LOCAL_TEST_DIRECTORY)


    def test_file_transfer_server_server(self):
        # test specific set up for transfer from local server to remote server (rocks)
        from_storage = self.storage_servers['local']
        to_storage = self.storage_servers['rocks']

        # creating the file resource
        _create_file_resource(count=1)
        file_resource = SequenceDataFile.objects.all()[0]

        # checking that the file does not already exist on the remote server from a previous test
        client, sftp = connect_sftp_server(to_storage.server_ip, to_storage.username)
        remote_filepath = os.path.join(to_storage.storage_directory, file_resource.filename)
        self.assertRaises(IOError, sftp.stat, remote_filepath)

        # removing all subdirectories in remote server if any created from a previous test
        cmd = str("rm -rf " + to_storage.storage_directory)
        client.exec_command(cmd)
        cmd2 = str("mkdir -p " + to_storage.storage_directory)
        client.exec_command(cmd2)
        client.close()

        # adding the file instance to the local server
        _add_file_instances_to_server(
            storage = from_storage,
            file_resource = file_resource,
            dnasequence = DNASequences.objects.all()[0],
            create=True
        )

        # creating the file transfer object
        file_transfer = FileTransfer(
            from_storage = from_storage,
            to_storage = to_storage,
            file_instance = FileInstance.objects.all()[0],
            new_filename=file_resource.filename
        )

        perform_transfer_file_server_server(file_transfer = file_transfer)

        # assert that the file exists on the remote server
        client, sftp = connect_sftp_server(to_storage.server_ip, to_storage.username)

        try:
            sftp.stat(remote_filepath)
            sftp.remove(remote_filepath)
        except:
            self.fail("Test for file transfer failed - {} was not found".format(remote_filepath))

        client.close()

    def test_file_transfer_server_server_FileDoesNotActuallyExist(self):
        # test specific set up for transfer from local server to remote server (rocks)
        from_storage = self.storage_servers['local']
        to_storage = self.storage_servers['rocks']

        # creating the file resource
        _create_file_resource(count=1)
        file_resource = SequenceDataFile.objects.all()[0]


        # add the file instance, but do NOT actually add the file - this is testing the exception is being thrown
        _add_file_instances_to_server(
            storage=from_storage,
            file_resource=file_resource,
            dnasequence=DNASequences.objects.all()[0],
            create=False
        )

        # make sure that the file was not created, and does not exist on the local server
        client, sftp = connect_sftp_server(to_storage.server_ip, to_storage.username)
        local_filepath = os.path.join(from_storage.storage_directory, file_resource.filename)
        self.assertRaises(IOError, sftp.stat, local_filepath)
        client.close()

        # create the file transfer object
        file_transfer = FileTransfer(
            from_storage=from_storage,
            to_storage=to_storage,
            file_instance=FileInstance.objects.all()[0],
            new_filename=file_resource.filename,
        )

        # assert exception is thrown
        self.assertRaises(FileDoesNotActuallyExist, perform_transfer_file_server_server, file_transfer)


    def test_file_transfer_server_azure(self):
        # test specific setup for local server transfer to cloud
        from_storage = self.storage_servers['local']
        to_storage = self.storage_servers['blob_storage']
        service = get_block_blob_service(to_storage)

        # creating file resource for test
        _create_file_resource(count=1)
        file_resource = SequenceDataFile.objects.all()[0]

        # clearing test cloud storage files
        _clear_test_cloud_storage(to_storage)

        # making sure cloud storage clear worked, and test file isn't already in the storage container
        for blob in service.list_blobs(to_storage.storage_container):
            if blob.name == file_resource.filename:
                self.fail()

        # add file instance for the cloud storage file, and create the file as well
        _add_file_instances_to_server(
            storage = from_storage,
            file_resource = file_resource,
            dnasequence = DNASequences.objects.all()[0],
            create = True
        )

        # this should reflect folder structure on cloud blob storage
        # when performing the file transfer, the root "/" should be stripped, otherwise it creates a
        # <no name> folder at the root of the cloud storage to act as the "root" folder
        file_transfer = FileTransfer(
            from_storage = from_storage,
            to_storage = to_storage,
            file_instance = FileInstance.objects.all()[0],
            new_filename = file_resource.filename,
        )

        perform_transfer_file_server_azure(file_transfer)

        # remember to strip the root "/" in tests, because we stripped this when transferring to the cloud
        self.assertTrue(file_resource.filename.strip("/") in [blob.name
                                          for blob in service.list_blobs(to_storage.storage_container)])


    def test_file_transfer_azure_server(self):
        # test specific set up for cloud transfer to local server
        from_storage = self.storage_servers['blob_storage']
        to_storage = self.storage_servers['local']
        service = get_block_blob_service(from_storage)

        # Create test file resource
        _create_file_resource(count=1)
        file_resource = SequenceDataFile.objects.all()[0]

        # file transfer location
        local_filename = os.path.join(to_storage.storage_directory, file_resource.filename)

        # Dummy file used in this test to populate the cloud
        source_filename = os.path.join(DIR_TO_POPULATE_CLOUD, FILE_TO_POPULATE_CLOUD)
        _clear_test_cloud_storage(from_storage)

        # make sure no test file from previous tests, or subdirectory structure in place already
        _clear_up_test_files(to_storage.storage_directory)
        self.assertFalse(os.path.isfile(local_filename))

        # file to populate test cloud storage
        self.assertTrue(os.path.isfile(source_filename))

        # uploading file to test cloud storage, remember to strip the slash! Otherwise this creates an additional
        # <no name> root folder
        service.create_blob_from_path(
            from_storage.storage_container,  # name of container
            file_resource.filename.strip("/"),  # name of the blob
            source_filename)
        self.assertTrue(file_resource.filename.strip("/") in [blob.name
                                                     for blob in service.list_blobs(from_storage.storage_container)])

        # creating file instance object and related file type object for the file on the test cloud storage
        _add_file_instances_to_cloud(
            storage = from_storage,
            file_resource = SequenceDataFile.objects.all()[0],
            dnasequence = DNASequences.objects.all()[0],
        )

        # creating file transfer object
        # note: the new_filename parameter is just the same name as the file resource's name
        # this is the intended behaviour for first phase of tantalus - this may change with later versions, so this test will likely break
        file_transfer = FileTransfer(
            from_storage = from_storage,
            to_storage = to_storage,
            file_instance = FileInstance.objects.all()[0],
            new_filename = file_resource.filename
        )

        # check if file exists after transfer
        perform_transfer_file_azure_server(file_transfer=file_transfer)
        self.assertTrue(os.path.isfile(
            os.path.join(to_storage.storage_directory, file_resource.filename.strip('/'))))

    def test_file_transfer_azure_server_FileDoesNotActuallyExist(self):
        # test specific set up
        from_storage = self.storage_servers['blob_storage']
        to_storage = self.storage_servers['local']

        # file resource for test
        _create_file_resource(count=1)
        file_resource = SequenceDataFile.objects.all()[0]

        # clear test cloud storage
        _clear_test_cloud_storage(from_storage)

        # creating file instance object and related file type object for the file on the test cloud storage
        _add_file_instances_to_cloud(
            storage=from_storage,
            file_resource=SequenceDataFile.objects.all()[0],
            dnasequence=DNASequences.objects.all()[0],
        )

        # creating file transfer object for test
        file_transfer = FileTransfer(
            from_storage=from_storage,
            to_storage=to_storage,
            file_instance=FileInstance.objects.all()[0],
            new_filename=file_resource.filename
        )

        # check that exception is thrown - no file on cloud actually exists for the file instance
        self.assertRaises(FileDoesNotActuallyExist, perform_transfer_file_azure_server, file_transfer)
