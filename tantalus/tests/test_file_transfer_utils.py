from django.test import TestCase, TransactionTestCase

from misc.update_tantalus_db import add_new_sequencelanes, add_new_libraries, add_new_samples
import socket, getpass
from tantalus.file_transfer_utils import *
from django.utils import timezone
import shutil
import subprocess

# TODO: remember to change this user to the user running the tests
SSH_USER = 'jngo'

## TEST CONSTANTS ##

# !!!! NOTE - NEVER PUT ANYTHING IMPORTANT IN THE TEST DIRECTORIES - THEY WILL BE WIPED AFTER EVERY TEST !!!!
COMPUTE2_TEST_DIRECTORY = "/home/{}/tantalus-test/".format(SSH_USER)
COMPUTE2_IP = "10.9.2.187"
COMPUTE2_LIMITED_SPACE_DIRECTORY = "/mnt/test" # this directory has 10mb of space

BEAST_TEST_DIRECTORY = "/home/{}/tantalus-test/".format(SSH_USER)
BEAST_IP = "10.9.4.26"

ROCKS_TEST_DIRECTORY = "/home/{}/tantalus-test/".format(SSH_USER)
ROCKS_IP = "10.9.4.27"

THOST_IP = '10.9.208.161'
THOST_TEST_DIRECTORY = "/genesis/shahlab/jngo/FAKE_DESTINATION_DIRECTORY/"

SHAHLAB15_TEST_DIRECTORY = "/home/{}/tantalus-test/".format(SSH_USER)
SHAHLAB15_IP = "10.9.215.80"

AZURE_STORAGE_ACCOUNT = "singlecellstorage"
AZURE_STORAGE_CONTAINER = "jess-testing"
AZURE_STORAGE_KEY = "okQAsp72BagVWpGLEaUNO30jH9XGLuVj3EDmbtg7oV6nmH7+9E+4csF+AXn4G3YMEKebnCnsRwVu9fRhh2RiMQ=="

LOCAL_USER = getpass.getuser()
LOCAL_TEST_DIRECTORY = os.path.join(os.path.realpath(os.path.dirname(__file__)),
                                    "test-file-destination-directory")
LOCAL_OTHER_TEST_DIRECTORY = os.path.join(os.path.realpath(os.path.dirname(__file__)),
                                    "other-test-file-destination-directory")

# TODO: replace this path with a huge file
PATH_TO_HUGE_FILE = "/Users/jngo/dummydir"
HUGE_FILE_FILENAME = "HUGE_FILE_OF_YES.txt"

# LOCAL_TEST_DIRECTORY = "/Users/jngo/cloud-test-file-transfer"
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
LOCAL_IP = s.getsockname()[0]
s.close()

# Test directory that contains test file to populate cloud for cloud - server transfer
DIR_TO_POPULATE_CLOUD = os.path.join(os.path.realpath(os.path.dirname(__file__)),
                                     "test-file-source-directory")
FILE_TO_POPULATE_CLOUD = "cloud-test-file"

# NOTE: this module is not responsible for creating subdirectories, so this should only be the filename,
# but in combination with other modules, this can become a relative path - just not in this testing module
BASE_FILENAME = "test_file"

# these are all dummy values for the file resource to be created
FILE_MD5 = "d41d8cd98f00b204e9800998ecf8427e"
FILE_SIZE = 0
FILE_CREATION_DATE = timezone.now()
FILE_TYPE = FileResource.FQ
FILE_COMPRESSION = FileResource.UNCOMPRESSED


## HELPER TEST FUNCTIONS ##
def connect_sftp_server(server_ip, username):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.connect(
        server_ip,
        username=username)
    sftp = paramiko.SFTPClient.from_transport(client.get_transport())
    return client, sftp


def _delete_local_test_files(directory_to_clean):
    if os.path.isdir(directory_to_clean):
        shutil.rmtree(directory_to_clean)
    os.mkdir(directory_to_clean)


def _delete_remote_test_files(directory_to_clean, client):
    cmd = "rm -rf " + directory_to_clean
    client.exec_command(cmd)

    cmd = "mkdir -p " + directory_to_clean
    client.exec_command(cmd)


def _clear_test_cloud_storage(blob_storage):
    service = get_block_blob_service(blob_storage)
    for blob in service.list_blobs(blob_storage.storage_container):
        service.delete_blob(blob_storage.storage_container, blob.name)


def _add_dataset(count, file_resource):
    for i in range(0, count):
        p = SingleEndFastqFile(dna_sequences=DNASequences.objects.all()[0])
        p.reads_file = file_resource
        p.save()
        p.lanes = SequenceLane.objects.all()[0],
        p.save()


def _add_file_resource():
    md5 = FILE_MD5

    file_resource = FileResource(
        md5=md5,
        size=FILE_SIZE,
        created=FILE_CREATION_DATE,
        file_type=FILE_TYPE,
        compression=FILE_COMPRESSION,
        filename=BASE_FILENAME,
    )
    file_resource.save()


def _add_file_instances_to_server(storage, file_resource, create=True):
    """
    Adds the file instance for the given file resource, and a SingleEndFastq instance to represent the file
    Has a create flag to determine whether or not the files are actually created on the servers

    :param storage:
    :param file_resource:
    :param create: if create is true, the files on the server will also be created,
    this is used to test the FileDoesNotExist exception - defaults to true otherwise
    :return:
    """
    serverfile = FileInstance(
        storage=storage,
        file_resource=file_resource,
    )
    serverfile.save()

    # creating files on the server
    if create:
        filepath = os.path.join(str(storage.storage_directory), serverfile.file_resource.filename)
        dirname, filename = os.path.split(filepath.rstrip('/'))
        cmd1 = "mkdir -p " + dirname
        cmd2 = "chmod -R 777 " + dirname
        cmd3 = "touch " + filepath
        if LOCAL_IP == storage.server_ip:
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


def _add_file_instances_to_cloud(storage, file_resource):
    serverfile = FileInstance(
        storage=storage,
        file_resource=file_resource,
    )
    serverfile.save()


## TESTS ##
class FileTransferTest(TransactionTestCase):
    """
    Tests for the file transfer utils. This does not test the celery tasks, or retrying them.

    NOTE:
    the TestCase test class does not commit changes to the database, so assertions about the object's state should not be used,
    they will not work.

    If testing with commits to the database are required, see documentation here on TransactionTestCase or SimpleTestCase:
    https://docs.djangoproject.com/en/1.9/topics/testing/tools/#provided-test-case-classes
    """

    def add_storages(self):
        print ServerStorage.objects.all()
        ServerStorage.objects.all().delete()
        self.rocks = ServerStorage.objects.create(
            name='rocks',
            server_ip=ROCKS_IP,
            storage_directory=ROCKS_TEST_DIRECTORY,
            username=SSH_USER,
        )
        # self.rocks.full_clean()
        # TODO: add full_clean methods?

        self.thost = ServerStorage.objects.create(
            name='thost',
            server_ip=THOST_IP,
            storage_directory=THOST_TEST_DIRECTORY,
            username=SSH_USER,
        )

        self.blob_storage = AzureBlobStorage.objects.create(
            name='azure_sc_fastqs',
            storage_account=AZURE_STORAGE_ACCOUNT,
            storage_container=AZURE_STORAGE_CONTAINER,
            storage_key=AZURE_STORAGE_KEY,
        )

        self.compute2 = ServerStorage.objects.create(
            name='compute2',
            server_ip=COMPUTE2_IP,
            storage_directory=COMPUTE2_TEST_DIRECTORY,
            username=SSH_USER,
        )

        self.beast = ServerStorage.objects.create(
            name='beast',
            server_ip=BEAST_IP,
            storage_directory=BEAST_TEST_DIRECTORY,
            username=SSH_USER,
        )

        self.local = ServerStorage.objects.create(
            name='jngo',
            server_ip=LOCAL_IP,
            storage_directory=LOCAL_TEST_DIRECTORY,
            username=SSH_USER,
        )

        self.other_local = ServerStorage.objects.create(
            name='other_jngo',
            server_ip=LOCAL_IP,
            storage_directory=LOCAL_OTHER_TEST_DIRECTORY,
            username=SSH_USER,
        )

    def setUp(self):
        _delete_local_test_files(LOCAL_TEST_DIRECTORY)
        _delete_local_test_files(LOCAL_OTHER_TEST_DIRECTORY)
        add_new_samples(['SA928'])
        add_new_libraries(['A90652A'])
        add_new_sequencelanes(['CB95TANXX_6'])
        self.add_storages()

        # setting up test wide variables
        _add_file_resource()
        self.file_resource = FileResource.objects.all()[0]
        self.dataset = _add_dataset(1, self.file_resource)

    def test_file_transfer_server_server_local(self):
        """ testing transfers from a server to the same server but in a different location """
        # test specific set up for transfer from local server to remote server (rocks)
        from_storage = self.local
        to_storage = self.other_local
        file_resource = self.file_resource

        # checking that the file does not already exist in the other location
        remote_filepath = os.path.join(to_storage.storage_directory, file_resource.filename)
        self.assertRaises(OSError, os.stat, remote_filepath)

        # adding the file instance to the local server
        _add_file_instances_to_server(storage=from_storage, file_resource=file_resource, create=True)

        # creating the file transfer object
        file_transfer = FileTransfer.objects.create(
            from_storage=from_storage,
            to_storage=to_storage,
            file_instance=FileInstance.objects.all()[0],
        )

        transfer_file_server_server(file_transfer=file_transfer)
        # check that no errors were thrown for the file transfer objects
        self.assertEqual("", file_transfer.message)

        # assert that the file exists on the remote server
        client, sftp = connect_sftp_server(to_storage.server_ip, to_storage.username)

        try:
            sftp.stat(remote_filepath)
            sftp.remove(remote_filepath)
        except:
            self.fail("Test for file transfer failed - {} was not found".format(remote_filepath))

        client.close()

    def test_file_transfer_server_server_local_FileDoesNotExist(self):
        # test specific set up for transfer from local server to other local location
        from_storage = self.local
        to_storage = self.other_local
        file_resource = self.file_resource

        # add the file instance, but do NOT actually add the file - this is testing the exception is being thrown
        _add_file_instances_to_server(storage=from_storage, file_resource=file_resource, create=False)

        # make sure that the file was not created, and does not exist on the local server
        local_filepath = os.path.join(from_storage.storage_directory, file_resource.filename)
        self.assertRaises(OSError, os.stat, local_filepath)

        # create the file transfer object
        file_transfer = FileTransfer.objects.create(
            from_storage=from_storage,
            to_storage=to_storage,
            file_instance=FileInstance.objects.all()[0],
        )

        # assert exception is thrown and error message is correct
        self.assertRaises(FileDoesNotExist, transfer_file_server_server, file_transfer)

    def test_file_transfer_server_server_local_FileAlreadyExists(self):
        # test specific set up for transfer from local server to other local location
        from_storage = self.local
        to_storage = self.other_local
        file_resource = self.file_resource

        # add the file instance to both locations
        _add_file_instances_to_server(storage=from_storage, file_resource=file_resource, create=True)
        _add_file_instances_to_server(storage=to_storage, file_resource=file_resource, create=True)

        # create the file transfer object
        file_transfer = FileTransfer.objects.create(
            from_storage=from_storage,
            to_storage=to_storage,
            file_instance=FileInstance.objects.all()[0],
        )

        # assert exception is thrown and error message is correct
        self.assertRaises(FileAlreadyExists, transfer_file_server_server, file_transfer)

    def test_file_transfer_server_server_remote(self):
        """ testing transfers from server (remote) to another server (local),
            using SFTP get from the local server, rather than SFTP put from remote"""
        # test specific set up for transfer from local server to remote server (rocks)
        from_storage = self.rocks
        to_storage = self.local
        file_resource = self.file_resource

        # checking that the file does not already exist on the server from a previous test
        _delete_local_test_files(to_storage.storage_directory)
        local_filepath = os.path.join(to_storage.storage_directory, file_resource.filename)
        self.assertRaises(OSError, os.stat, local_filepath)

        # adding the file instance to the remote server for test
        # client, sftp = connect_sftp_server(from_storage.server_ip, from_storage.username)
        _add_file_instances_to_server(storage=from_storage, file_resource=file_resource, create=True)

        # creating the file transfer object
        file_transfer = FileTransfer.objects.create(
            from_storage=from_storage,
            to_storage=to_storage,
            file_instance=FileInstance.objects.all()[0],
        )

        transfer_file_server_server(file_transfer=file_transfer)
        # check that no errors were thrown for the file transfer objects
        self.assertEqual("", file_transfer.message)

        # assert that the file exists on the server after transfer
        try:
            os.stat(local_filepath)
            os.remove(local_filepath)
        except:
            self.fail("Test for file transfer failed - {} was not found".format(local_filepath))

    def test_file_transfer_server_server_remote_FileDoesNotExist(self):
        # test specific set up for transfer from local server to remote server (rocks)
        from_storage = self.rocks
        to_storage = self.local
        file_resource = self.file_resource

        client, sftp = connect_sftp_server(from_storage.server_ip, from_storage.username)
        _delete_remote_test_files(from_storage.storage_directory, client)

        # add the file instance, but do NOT actually add the file - this is testing the exception is being thrown
        _add_file_instances_to_server(storage=from_storage, file_resource=file_resource, create=False)

        # make sure that the file was not created, and does not exist on the remote server
        remote_filepath = os.path.join(from_storage.storage_directory, file_resource.filename)
        self.assertRaises(IOError, sftp.stat, remote_filepath)
        client.close()

        # create the file transfer object
        file_transfer = FileTransfer.objects.create(
            from_storage=from_storage,
            to_storage=to_storage,
            file_instance=FileInstance.objects.all()[0],
        )

        # assert exception is thrown
        self.assertRaises(FileDoesNotExist, transfer_file_server_server, file_transfer)

    def test_file_transfer_server_server_remote_FileAlreadyExists(self):
        # test specific set up for transfer from local server to remote server (rocks)
        from_storage = self.rocks
        to_storage = self.local
        file_resource = self.file_resource

        client, sftp = connect_sftp_server(from_storage.server_ip, from_storage.username)
        _delete_remote_test_files(from_storage.storage_directory, client)

        # add the file instance, but do NOT actually add the file - this is testing the exception is being thrown
        _add_file_instances_to_server(storage=from_storage, file_resource=file_resource, create=True)
        _add_file_instances_to_server(storage=to_storage, file_resource=file_resource, create=True)

        # create the file transfer object
        file_transfer = FileTransfer.objects.create(
            from_storage=from_storage,
            to_storage=to_storage,
            file_instance=FileInstance.objects.all()[0],
        )

        # assert exception is thrown
        self.assertRaises(FileAlreadyExists, transfer_file_server_server, file_transfer)


    def deactivated_test_file_transfer_server_server_EnvironmentError_broken_pipe(self):
        """
        THIS TEST MUST BE MANUALLY RUN WITH A LARGE FILE.

        1. Create or point at a large file (~2-3Gb in size), I create mine with the following command in a terminal:
        "yes > HUGE_FILE_OF_YES.txt"
        The larger the file size, the more time you have to complete steps 5-8.

        2. Change the HUGE_FILE_FILENAME to the filename. Eg. "HUGE_FILE_OF_YES.txt"

        3. Change the PATH_TO_HUGE_FILE variable to be the path of where the large file is located

        4. run only this test

        5. ssh into rocks and use the following command: ps -aux | grep ssh | grep jngo
            NOTE: replace jngo with with ROCKS_USER

        6. get the pid of the following process "/usr/libexec/openssh/sftp-server"

        7. kill the process, by using the kill command. Eg: kill 28404

        8. upon killing the process, this test should pass
        """
        # start a big file transfer
        # search for process id
        # kill it while transferring

        # test specific set up for transfer from local server to remote server (rocks)
        from_storage = ServerStorage.objects.create(
            name='jngo_large_file',
            server_ip=LOCAL_IP,
            storage_directory=PATH_TO_HUGE_FILE,
            username=SSH_USER,
        )

        to_storage = self.rocks

        # Making custom file resource for the large file
        file_resource = FileResource.objects.create(
            md5="12345",
            size=FILE_SIZE,
            created=FILE_CREATION_DATE,
            file_type=FILE_TYPE,
            compression=FILE_COMPRESSION,
            filename=HUGE_FILE_FILENAME
        )

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
        _add_file_instances_to_server(storage=from_storage, file_resource=file_resource, create=True)

        # creating the file transfer object - this file transfer is huge
        file_transfer = FileTransfer.objects.create(
            from_storage=from_storage,
            to_storage=to_storage,
            file_instance=FileInstance.objects.all()[0],
        )
        file_transfer.full_clean()
        file_transfer.save()

        # self.assertRaises(EnvironmentError, transfer_file_server_server, file_transfer)
        self.fail() # Please see test comments, comment this line out, and then uncomment the above 2 lines to run this test

    def deactivated_test_file_transfer_server_server_EnvironmentError_no_disk_space(self):
        self.fail("This no longer needs to be tested in this module - test somewhere else, probably deployment?")
        # test specific set up for transfer from local server to remote server with very small storage - 10 mb(compute2_limited_space)
        local_large_file_storage = ServerStorage.objects.create(
            name='jngo_large_file',
            server_ip=LOCAL_IP,
            storage_directory=PATH_TO_HUGE_FILE,
            username=SSH_USER,
        )

        compute2_limited_space = ServerStorage(
            name='compute2_limited_space',
            server_ip=COMPUTE2_IP,
            storage_directory=COMPUTE2_LIMITED_SPACE_DIRECTORY,
            username=SSH_USER,
        )
        # compute2_limited_space.full_clean()
        compute2_limited_space.save()

        from_storage = local_large_file_storage
        to_storage = compute2_limited_space

        # Making custom file resource for the large file
        file_resource = FileResource.objects.create(
            md5="12345",
            size=FILE_SIZE,
            created=FILE_CREATION_DATE,
            file_type=FILE_TYPE,
            compression=FILE_COMPRESSION,
            filename=HUGE_FILE_FILENAME
        )

        # adding the file instance to the local server
        _add_file_instances_to_server(storage=from_storage, file_resource=file_resource, create=True)

        # creating the file transfer object - this file transfer is huge
        file_transfer = FileTransfer.objects.create(
            from_storage=from_storage,
            to_storage=to_storage,
            file_instance=FileInstance.objects.all()[0],
        )
        file_transfer.full_clean()
        file_transfer.save()

        # perform_transfer_file_server_server(file_transfer)
        # check that correct error is thrown along with the updated error message
        self.assertRaises(EnvironmentError, transfer_file_server_server, file_transfer)
        error_message = "Failure - No specific error code was given.\nPossible reasons include:\n- A file is being uploaded to a full filesystem - available disk space is 2 kilobytes"
        self.assertEqual(error_message, file_transfer.message)

        # clean up test file
        client, sftp = connect_sftp_server(to_storage.server_ip, to_storage.username)
        testfile_path = os.path.join(to_storage.storage_directory, file_resource.filename)
        sftp.remove(testfile_path)
        client.close()

    def test_file_transfer_server_azure(self):
        # test specific setup for local server transfer to cloud
        from_storage = self.local
        to_storage = self.blob_storage
        service = get_block_blob_service(to_storage)
        file_resource = self.file_resource

        # clearing test cloud storage files
        _clear_test_cloud_storage(to_storage)

        # making sure cloud storage clear worked, and test file isn't already in the storage container
        for blob in service.list_blobs(to_storage.storage_container):
            if blob.name == file_resource.filename:
                self.fail()

        # add file instance for the file, and create the file as well
        _add_file_instances_to_server(storage=from_storage, file_resource=file_resource, create=True)

        # this should reflect folder structure on cloud blob storage
        # when performing the file transfer, the root "/" should be stripped, otherwise it creates a
        # <no name> folder at the root of the cloud storage to act as the "root" folder
        file_transfer = FileTransfer.objects.create(
            from_storage=from_storage,
            to_storage=to_storage,
            file_instance=FileInstance.objects.all()[0],
        )

        transfer_file_server_azure(file_transfer)

        # remember to strip the root "/" in tests, because we stripped this when transferring to the cloud
        self.assertTrue(file_resource.filename.strip("/") in [blob.name
                                                              for blob in service.list_blobs(to_storage.storage_container)])
        # check that no errors were thrown for the file transfer objects
        self.assertEquals("", file_transfer.message)

    def test_file_transfer_server_azure_FileDoesNotExist(self):
        # test specific setup for local server transfer to cloud
        from_storage = self.local
        to_storage = self.blob_storage
        service = get_block_blob_service(to_storage)
        file_resource = self.file_resource

        # clearing test cloud storage files
        _clear_test_cloud_storage(to_storage)

        # making sure cloud storage clear worked, and test file isn't already in the storage container
        for blob in service.list_blobs(to_storage.storage_container):
            if blob.name == file_resource.filename:
                self.fail()

        # add file instance for the file, and do NOT create the file
        _add_file_instances_to_server(storage=from_storage, file_resource=file_resource, create=False)

        # this should reflect folder structure on cloud blob storage
        # when performing the file transfer, the root "/" should be stripped, otherwise it creates a
        # <no name> folder at the root of the cloud storage to act as the "root" folder
        file_transfer = FileTransfer.objects.create(
            from_storage=from_storage,
            to_storage=to_storage,
            file_instance=FileInstance.objects.all()[0],
        )

        # check that exception is thrown - no file on server actually exists for the file instance
        self.assertRaises(FileDoesNotExist, transfer_file_server_azure, file_transfer)

    def test_file_transfer_server_azure_FileAlreadyExists(self):
        # test specific setup for local server transfer to cloud
        from_storage = self.local
        to_storage = self.blob_storage
        service = get_block_blob_service(to_storage)
        file_resource = self.file_resource

        # clearing test cloud storage files
        _clear_test_cloud_storage(to_storage)

        # add file instance for the file, and create the file as well
        _add_file_instances_to_server(storage=from_storage, file_resource=file_resource, create=True)

        # add the file to the cloud and check that it's there
        service.create_blob_from_path(
            to_storage.storage_container,  # name of container
            file_resource.filename.strip("/"),  # name of the blob
            os.path.join(from_storage.storage_directory, file_resource.filename)
        )
        self.assertTrue(file_resource.filename.strip("/") in [blob.name
                                                              for blob in
                                                              service.list_blobs(to_storage.storage_container)])

        # create the file transfer
        file_transfer = FileTransfer.objects.create(
            from_storage=from_storage,
            to_storage=to_storage,
            file_instance=FileInstance.objects.all()[0],
        )

        # check that exception is thrown - file already exists on the blob storage
        self.assertRaises(FileAlreadyExists, transfer_file_server_azure, file_transfer)

        # clean test file
        _clear_test_cloud_storage(to_storage)

    def test_file_transfer_azure_server(self):
        # test specific set up for cloud transfer to local server
        from_storage = self.blob_storage
        to_storage = self.local
        service = get_block_blob_service(from_storage)
        file_resource = self.file_resource

        # file transfer location
        local_filename = os.path.join(to_storage.storage_directory, file_resource.filename)

        # Dummy file used in this test to populate the cloud
        source_filename = os.path.join(DIR_TO_POPULATE_CLOUD, FILE_TO_POPULATE_CLOUD)
        _clear_test_cloud_storage(from_storage)

        # make sure no test file from previous tests, or subdirectory structure in place already
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
        _add_file_instances_to_cloud(storage=from_storage, file_resource=file_resource)

        # creating file transfer object
        file_transfer = FileTransfer.objects.create(
            from_storage=from_storage,
            to_storage=to_storage,
            file_instance=FileInstance.objects.all()[0],
        )

        # check if file exists after transfer
        transfer_file_azure_server(file_transfer=file_transfer)
        self.assertTrue(os.path.isfile(
            os.path.join(to_storage.storage_directory, file_resource.filename.strip('/'))))

    def test_file_transfer_azure_server_FileDoesNotExist(self):
        # test specific set up
        from_storage = self.blob_storage
        to_storage = self.local
        file_resource = self.file_resource

        # clear test cloud storage
        _clear_test_cloud_storage(from_storage)

        # creating file instance object and related file type object for the file on the test cloud storage
        _add_file_instances_to_cloud(storage=from_storage, file_resource=file_resource)

        # creating file transfer object for test
        file_transfer = FileTransfer.objects.create(
            from_storage=from_storage,
            to_storage=to_storage,
            file_instance=FileInstance.objects.all()[0],
        )

        # check that exception is thrown - no file on cloud actually exists
        self.assertRaises(FileDoesNotExist, transfer_file_azure_server, file_transfer)

    def test_file_transfer_azure_server_FileAlreadyExists(self):
        # test specific set up for cloud transfer to local server
        from_storage = self.blob_storage
        to_storage = self.local
        service = get_block_blob_service(from_storage)
        file_resource = self.file_resource

        # file transfer location
        local_filename = os.path.join(to_storage.storage_directory, file_resource.filename)

        # Dummy file used in this test to populate the cloud
        source_filename = os.path.join(DIR_TO_POPULATE_CLOUD, FILE_TO_POPULATE_CLOUD)
        _clear_test_cloud_storage(from_storage)

        # make sure no test file from previous tests, or subdirectory structure in place already
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
        _add_file_instances_to_cloud(storage=from_storage, file_resource=file_resource)

        # creating file transfer object
        file_transfer = FileTransfer.objects.create(
            from_storage=from_storage,
            to_storage=to_storage,
            file_instance=FileInstance.objects.all()[0],
        )

        # add file to local storage
        _add_file_instances_to_server(storage=to_storage, file_resource=file_resource, create=True)

        # check that exception is thrown - File already exists
        self.assertRaises(FileAlreadyExists, transfer_file_azure_server, file_transfer)

    def deactivated_test_file_transfer_azure_server_data_corruption_empty_file_sent(self):
        self.fail("this test is no longer needed in this module - move to another test module?")
        # test specific set up
        from_storage = self.blob_storage
        to_storage = self.local
        service = get_block_blob_service(from_storage)

        # changing file resource md5 to an incorrect md5 with non zero filesize to test datacorruption exception
        file_resource = self.file_resource
        file_resource.md5 = "ThisIsAnIncorrectMD5sum"
        file_resource.size = 3 # non zero file size
        file_resource.save()

        # clear test cloud storage
        _clear_test_cloud_storage(from_storage)

        # file transfer location
        local_filename = os.path.join(to_storage.storage_directory, file_resource.filename)

        # Dummy file used in this test to populate the cloud
        source_filename = os.path.join(DIR_TO_POPULATE_CLOUD, FILE_TO_POPULATE_CLOUD)
        _clear_test_cloud_storage(from_storage)

        # make sure no test file from previous tests, or subdirectory structure in place already
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
                                                              for blob in
                                                              service.list_blobs(from_storage.storage_container)])

        # creating file instance object and related file type object for the file on the test cloud storage
        _add_file_instances_to_cloud(storage=from_storage, file_resource=file_resource)

        # creating file transfer object for test
        file_transfer = FileTransfer.objects.create(
            from_storage=from_storage,
            to_storage=to_storage,
            file_instance=FileInstance.objects.all()[0],
        )

        self.assertRaises(DataCorruptionError, transfer_file_azure_server, file_transfer)
        # check error message for file transfer object is correct
        error_message = "Null MD5 hash for file but file should not be size 0"
        self.assertEquals(error_message, file_transfer.message)

    def deactivated_test_file_transfer_azure_server_data_corruption_corrupted_file_sent(self):
        self.fail("this test is no longer needed in this module - move to another test module?")
        # test specific set up
        from_storage = self.blob_storage
        to_storage = self.local
        service = get_block_blob_service(from_storage)

        # changing file resource md5 to an incorrect md5 with non zero filesize to test datacorruption exception
        file_resource = self.file_resource
        file_resource.md5 = "ThisIsAnIncorrectMD5sum"
        file_resource.size = 100 # non zero file size
        file_resource.save()

        # clear test cloud storage
        _clear_test_cloud_storage(from_storage)

        # file transfer location
        local_filename = os.path.join(to_storage.storage_directory, file_resource.filename)

        # Dummy file used in this test to populate the cloud
        source_filename = os.path.join(DIR_TO_POPULATE_CLOUD, FILE_TO_POPULATE_CLOUD)

        # give the dummy file some content
        with open(source_filename, 'a+') as dummy_file:
            dummy_file.write("make this a non empty file")
        _clear_test_cloud_storage(from_storage)

        # make sure no test file from previous tests, or subdirectory structure in place already
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
                                                              for blob in
                                                              service.list_blobs(from_storage.storage_container)])

        # creating file instance object and related file type object for the file on the test cloud storage
        _add_file_instances_to_cloud(storage=from_storage, file_resource=file_resource)

        # creating file transfer object for test
        file_transfer = FileTransfer.objects.create(
            from_storage=from_storage,
            to_storage=to_storage,
            file_instance=FileInstance.objects.all()[0],
        )

        # make the source file empty again:
        with open(source_filename, 'w+') as dummy_file:
            dummy_file.write("")

        # check the DataCorruptionError is thrown and error message for file transfer object is correct
        self.assertRaises(DataCorruptionError, transfer_file_azure_server, file_transfer)
        error_message = "Data has been corrupted - file md5 is 67a995130dbea46252f46f42580eb688 while database md5 is ThisIsAnIncorrectMD5sum"
        self.assertEquals(error_message,
                          file_transfer.message)