from django.test import TestCase

from tantalus.models import *
from misc.update_tantalus_db import add_new_samples, add_new_libraries, add_new_sequencelanes
from loaders.load_single_cell_table import load_library_and_get_data, create_reads_file
from rest_framework.test import APIRequestFactory, force_authenticate, APITestCase
from account.models import User
from rest_framework import status
from django.urls import reverse
import requests


AZURE_STORAGE_ACCOUNT = "singlecellstorage"
AZURE_STORAGE_CONTAINER = "jess-testing"
AZURE_STORAGE_KEY = "okQAsp72BagVWpGLEaUNO30jH9XGLuVj3EDmbtg7oV6nmH7+9E+4csF+AXn4G3YMEKebnCnsRwVu9fRhh2RiMQ=="

def add_test_storages():
    test_rocks = ServerStorage(
        name='test_rocks',
        server_ip='rocks3.cluster.bccrc.ca',
        storage_directory='/share/lustre/jngo',
        username='jngo',
    )
    test_rocks.full_clean()
    test_rocks.save()

    test_thost = ServerStorage(
        name='test_rocks',
        server_ip='rocks3.cluster.bccrc.ca',
        storage_directory='/share/lustre/jngo',
        username='jngo',
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
        'test_rocks':test_rocks,
        'test_thost': test_thost,
        'blob_storage':blob_storage,
    }

    return storages


class DeploymentAPITest(APITestCase):

    storage_servers = {}

    @classmethod
    def setUpTestData(cls):
        add_new_samples(['SA928'])
        add_new_libraries(['A90652A'])
        add_new_sequencelanes(['CB95TANXX_6'])

        cls.storage_servers = add_test_storages()

        # pull filepaths for the given GSC Library ID
        data = load_library_and_get_data(gsc_library_id="PX0593")

        # creating file resources, and also file instances for given GSC library ID
        # Note that to create the file names, the "storage directory" part of the path must be stripped away
        create_reads_file(data, cls.storage_servers['test_rocks'],
                          directory_to_strip="/share/lustre/archive/single_cell_indexing/HiSeq/")

        # creating authenticated user
        cls.user = User.objects.create_user(
            username='jngo',
            email='jngo@bccrc.ca',
            password='thisisasupersecretpassword!'
        )


    def test_create_deployment_valid(self):
        dataset = AbstractDataSet.objects.all()
        dataset = [dataset[0].id, dataset[1].id]

        from_storage = self.storage_servers['test_rocks']
        to_storage = self.storage_servers['test_thost']

        data = {
            "from_storage": from_storage.id,
            "to_storage": to_storage.id,
            "datasets": dataset
        }

        self.client.force_login(self.user)
        response = self.client.post(reverse('deployment-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # checking deployment is created correctly
        self.assertEquals(Deployment.objects.all().count(), 1)
        deployment = Deployment.objects.all()[0]
        self.assertEqual(deployment.from_storage, from_storage)
        self.assertEqual(deployment.to_storage, to_storage)

    def test_create_deployment_already_existing_deployment(self):
        dataset = AbstractDataSet.objects.all()
        dataset = [dataset[0].id, dataset[1].id]

        from_storage = self.storage_servers['test_rocks']
        to_storage = self.storage_servers['test_thost']

        data = {
            "from_storage": from_storage.id,
            "to_storage": to_storage.id,
            "datasets": dataset
        }

        self.client.force_login(self.user)
        response = self.client.post(reverse('deployment-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # checking deployment is created correctly
        response = self.client.post(reverse('deployment-list'), data, format='json')
        print response
        self.assertEquals(Deployment.objects.all().count(), 1)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        #TODO: make code pass this test