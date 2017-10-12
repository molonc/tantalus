from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase, APISimpleTestCase, APITransactionTestCase
from rest_framework import status

import paramiko, time, os

from tantalus.models import *
from misc.update_tantalus_db import add_new_samples, add_new_libraries, add_new_sequencelanes
from loaders.load_single_cell_table import load_library_and_get_data, create_reads_file
from account.models import User
import requests


AZURE_STORAGE_ACCOUNT = "singlecellstorage"
AZURE_STORAGE_CONTAINER = "jess-testing"
AZURE_STORAGE_KEY = "okQAsp72BagVWpGLEaUNO30jH9XGLuVj3EDmbtg7oV6nmH7+9E+4csF+AXn4G3YMEKebnCnsRwVu9fRhh2RiMQ=="

# WARNING: EVERYTHING IN THIS TEST DIRECTORY WILL GET WIPED AFTER EVERY TEST!
TEST_THOST_IP = '10.9.208.161'
REMOTE_THOST_TEST_DIRECTORY = "/genesis/shahlab/jngo/FAKE_DESTINATION_DIRECTORY/"
TEST_THOST_USER = 'jngo'

# Source of test files for transfers
TEST_FILE_STORAGE = '/share/lustre/jngo'

SLEEP_INTERVAL_SECONDS = 10
MAX_NUM_ATTEMPTS = 10


def add_test_storages():
    test_rocks = ServerStorage(
        name='test_rocks',
        server_ip='rocks3.cluster.bccrc.ca',
        storage_directory=TEST_FILE_STORAGE,
        username='jngo',
    )
    test_rocks.full_clean()
    test_rocks.save()

    test_thost = ServerStorage(
        name='test_thost',
        server_ip=TEST_THOST_IP,
        storage_directory=REMOTE_THOST_TEST_DIRECTORY,
        username=TEST_THOST_USER,
    )
    test_thost.full_clean()
    test_thost.save()

    blob_storage = AzureBlobStorage(
        name='azure_sc_fastqs',
        storage_account=AZURE_STORAGE_ACCOUNT,
        storage_container=AZURE_STORAGE_CONTAINER,
        storage_key=AZURE_STORAGE_KEY,
    )
    blob_storage.full_clean()
    blob_storage.save()

    storages = {
        'test_rocks': test_rocks,
        'test_thost': test_thost,
        'blob_storage': blob_storage,
    }

    return storages


def _clear_remote_test_files():
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.connect(
        TEST_THOST_IP,
        username=TEST_THOST_USER)
    cmd = "rm -rf " + REMOTE_THOST_TEST_DIRECTORY
    stdin, stdout, stderr = client.exec_command(cmd)
    stderr.channel.recv_exit_status()
    cmd2 = "mkdir " + REMOTE_THOST_TEST_DIRECTORY
    stdin, stdout, stderr = client.exec_command(cmd2)
    stderr.channel.recv_exit_status()


def connect_sftp_server(server_ip, username):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.connect(
        server_ip,
        username=username)
    sftp = paramiko.SFTPClient.from_transport(client.get_transport())
    return client, sftp


class DeploymentAPITest(APITransactionTestCase):
    """
    These tests are run based on data loaded from the single_cell_hiseq_fastq.tsv file found in the loaders module
    Therefore, for these tests, it is assumed that:
    1. There are no FileInstance objects loaded into the test database that already exist at thost,
    2. All of the (valid) FileInstance objects used for this testing module have a physical file saved at TEST_FILE_STORAGE

    """

    def add_storages(self):
        self.test_rocks = ServerStorage.objects.create(
            name='test_rocks',
            server_ip='rocks3.cluster.bccrc.ca',
            storage_directory='/share/lustre/jngo',
            username='jngo',
        )

        self.test_thost = ServerStorage.objects.create(
            name='test_thost',
            server_ip=TEST_THOST_IP,
            storage_directory=REMOTE_THOST_TEST_DIRECTORY,
            username=TEST_THOST_USER,
        )

        self.blob_storage = AzureBlobStorage.objects.create(
            name='azure_sc_fastqs',
            storage_account=AZURE_STORAGE_ACCOUNT,
            storage_container=AZURE_STORAGE_CONTAINER,
            storage_key=AZURE_STORAGE_KEY,
        )

    def setUp(self):
        _clear_remote_test_files()
        add_new_samples(['SA928'])
        add_new_libraries(['A90652A'])
        add_new_sequencelanes(['CB95TANXX_6'])
        self.add_storages()
        self.user = User.objects.create_user(
            username='jngo',
            email='jngo@bccrc.ca',
            password='thisisasupersecretpassword!',
        )

        # pull filepaths for the given GSC Library ID
        data = load_library_and_get_data(gsc_library_id="PX0593")

        # creates file resources, and also file instances for given GSC library ID
        # Note that to create the file names, the "storage directory" part of the path must be stripped away
        create_reads_file(data, self.test_rocks,
                          directory_to_strip="/share/lustre/archive/single_cell_indexing/HiSeq/")

    def post_deployment_api(self, data):
        self.client.force_login(self.user)
        print "making API request with the following response: "
        response = self.client.post(reverse('api:deployment-list'), data, format='json')
        print response
        return response

    def test_create_deployment_valid(self):
        dataset = AbstractDataSet.objects.all()
        dataset_ids = [dataset[0].id, dataset[1].id]

        from_storage = self.test_rocks
        to_storage = self.test_thost

        data = {
            "from_storage": from_storage.id,
            "to_storage": to_storage.id,
            "datasets": dataset_ids
        }

        client, sftp = connect_sftp_server(to_storage.server_ip, to_storage.username)
        response = self.post_deployment_api(data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        # check that the deployment and the associated file transfers were created
        self.assertEqual(1, Deployment.objects.all().count())

        # deployment and associated file transfer objects
        deployment = Deployment.objects.all()[0]
        file_transfers = deployment.file_transfers.all()

        # test that the created deployment is correct
        self.assertEqual(from_storage, deployment.from_storage)
        self.assertEqual(to_storage, deployment.to_storage)
        self.assertEqual(4, file_transfers.count())

        # TODO: test progress of file transfer and status of file?
        num_physical_files = 0
        num_complete_file_transfers = 0
        physical_transfer_complete = False
        file_transfer_object_complete = False
        for i in range(0, MAX_NUM_ATTEMPTS):
            # both physical file transfer, and file transfer objects are executed/updated successfully
            if physical_transfer_complete and file_transfer_object_complete:
                break

            # otherwise timeout, and try again after the interval
            time.sleep(SLEEP_INTERVAL_SECONDS)

            # checking whether physical file transfer is complete, and whether file transfer objects reflect completion status
            print "this is attempt " + str(i)
            for file_transfer in deployment.file_transfers.all():
                print "progress of file transfer with pk: {} is at {}".format(file_transfer.pk, file_transfer.progress)
                remote_path = os.path.join(to_storage.storage_directory, file_transfer.new_filename)

                if file_transfer.finished:
                    num_complete_file_transfers = num_complete_file_transfers + 1
                try:
                    sftp.stat(remote_path)
                    num_physical_files = num_physical_files + 1
                except IOError:
                    break

                # checking whether physical file transfer is complete &
                # checking whether file transfer objects reflect completion status
                if num_physical_files == file_transfers.count():
                    physical_transfer_complete = True
                if num_complete_file_transfers == file_transfers.count():
                    file_transfer_object_complete = True
                    break
            num_complete_file_transfers = 0
            num_physical_files = 0

        # assert that files are actually transferred into storage
        self.assertTrue(physical_transfer_complete)
        # assert that the file transfers objects are updated correctly
        for file_transfer in file_transfers:
            self.assertEqual(1, file_transfer.progress)
            self.assertTrue(file_transfer.finished)
            self.assertFalse(file_transfer.running)
            self.assertTrue(file_transfer.success)

    def test_create_deployment_deploymentnotcreated__fileinstance_already_deployed(self):
        dataset = AbstractDataSet.objects.all()[0]
        from_storage = self.test_rocks
        to_storage = self.test_thost

        fileresource = dataset.get_data_fileset()[0]

        # checking precondition that FileResource has an existing FileInstance at from_storage and none at to_storage
        self.assertIn("test_rocks", fileresource.fileinstance_set.all().values_list('storage__name', flat=True))
        self.assertNotIn("test_thost", fileresource.fileinstance_set.all().values_list('storage__name', flat=True))

        # creating file instance at the to_storage location for the given FileResource
        FileInstance.objects.create(
            storage=to_storage,
            file_resource=fileresource,
        )

        data = {
            "from_storage": from_storage.id,
            "to_storage": to_storage.id,
            "datasets": [dataset.id]
        }

        response = self.post_deployment_api(data)

        # checking response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        ERROR_STRING = "file instance for file resource {} already deployed on test_thost".format(fileresource.filename)
        ERROR_JSON_RESPONSE = "{{\"detail\":\"{error_string}\"}}".format(error_string=ERROR_STRING)
        self.assertEqual(ERROR_JSON_RESPONSE, response.content)

        # check that the deployment and the associated file transfers were NOT created
        self.assertEqual(0, Deployment.objects.all().count())
        self.assertEqual(0, FileTransfer.objects.all().count())

    def test_create_deployment_deploymentnotcreated__fileinstance_not_deployed_on_from_storage(self):
        dataset = AbstractDataSet.objects.all()[0]
        from_storage = self.test_thost
        to_storage = self.blob_storage

        fileresource = dataset.get_data_fileset()[0]

        # checking precondition that FileResource has NO FileInstance at from_storage
        # using thost as from_storage for this
        self.assertNotIn("test_thost", fileresource.fileinstance_set.all().values_list('storage__name', flat=True))
        data = {
            "from_storage": from_storage.id,
            "to_storage": to_storage.id,
            "datasets": [dataset.id]
        }

        response = self.post_deployment_api(data)

        # checking response
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        ERROR_STRING = "file instance for file resource {} not deployed on source storage test_thost".format(fileresource.filename)
        ERROR_JSON_RESPONSE = "{{\"detail\":\"{error_string}\"}}".format(error_string=ERROR_STRING)
        self.assertEqual(ERROR_JSON_RESPONSE, response.content)

        # check that the deployment and the associated file transfers were NOT created
        self.assertEqual(0, Deployment.objects.all().count())
        self.assertEqual(0, FileTransfer.objects.all().count())

    def test_create_deployment_deploymentnotcreated__multiple_filetransfer_already_exists(self):
        dataset = AbstractDataSet.objects.all()[0]
        from_storage = self.test_rocks
        to_storage = self.test_thost
        fake_storage1 = ServerStorage.objects.create(
            name='fake_storage1',
            server_ip='dummy_ip1',
            storage_directory='/fake/storage',
            username='jngo',
        )

        fake_storage2 = ServerStorage.objects.create(
            name='fake_storage2',
            server_ip='dummy_ip2',
            storage_directory='/fake/storage2',
            username='jngo',
        )

        fileresource = dataset.get_data_fileset()[0]

        # file instances for the file resource
        # the only loaded fileinstance for the file resource based on loading for these tests should be for rocks
        rocks_fileinstance = fileresource.fileinstance_set.all()[0]
        self.assertEqual(self.test_rocks, rocks_fileinstance.storage)

        # creating another fileinstance for the same file resource
        dummy_fileinstance = FileInstance(
            storage=fake_storage1,
            file_resource=fileresource,
        )
        dummy_fileinstance.save()

        # creating another fileinstance for the same file resource
        dummy_fileinstance2 = FileInstance(
            storage=fake_storage2,
            file_resource=fileresource,
        )
        dummy_fileinstance2.save()

        # creating filetransfer for fake_storage1 to to_storage
        existing_filetransfer = FileTransfer(
            from_storage=from_storage,
            to_storage=to_storage,
            file_instance=dummy_fileinstance,
        )
        existing_filetransfer.save()

        # creating filetransfer for fake_storage1 to to_storage
        existing_filetransfer2 = FileTransfer(
            from_storage=from_storage,
            to_storage=to_storage,
            file_instance=dummy_fileinstance2,
        )
        existing_filetransfer2.save()

        print fileresource.fileinstance_set
        print "there should be 3!"
        print fileresource.fileinstance_set.count()
        data = {
            "from_storage": from_storage.id,
            "to_storage": to_storage.id,
            "datasets": [dataset.id]
        }

        response = self.post_deployment_api(data)

        # post request should not be successful, and object should not be created
        self.assertEqual(0, Deployment.objects.all().count())
        # the two dummy file transfers that we made should amount to 2
        self.assertEqual(2, FileTransfer.objects.all().count())

        # checking response
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        ERROR_STRING = "multiple existing transfers for {} to test_thost - Contact database admin".format(fileresource.filename)
        ERROR_JSON_RESPONSE = "{{\"detail\":\"{error_string}\"}}".format(error_string=ERROR_STRING)
        self.assertEqual(ERROR_JSON_RESPONSE, response.content)

    def test_create_deployment_already_existing_deployment(self):
        dataset = AbstractDataSet.objects.all()
        dataset = [dataset[0].id, dataset[1].id]

        from_storage = self.test_rocks
        to_storage = self.test_thost

        data = {
            "from_storage": from_storage.id,
            "to_storage": to_storage.id,
            "datasets": dataset
        }

        # creating the duplicate deployment for this test
        d = Deployment(
            from_storage=from_storage,
            to_storage=to_storage,
        )
        d.save()
        d.datasets = [dataset[0], dataset[1]]
        d.save()

        # posting to create another deployment with the same data
        response = self.post_deployment_api(data)

        # post request should not be successful, and object should not be created
        self.assertEqual(1, Deployment.objects.all().count())
        self.assertEqual(4, FileTransfer.objects.all().count())
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

        #TODO: make code pass this test
        self.fail()