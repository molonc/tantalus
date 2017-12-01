from __future__ import absolute_import
from tantalus.models import FileTransfer
import tantalus.tasks
from celery import chain
import pandas as pd


def start_file_transfer(file_transfer):
    """
    Start a single file transfer.
    """

    from_storage_type = file_transfer.from_storage.__class__.__name__
    to_storage_type = file_transfer.to_storage.__class__.__name__

    if from_storage_type == 'ServerStorage' and to_storage_type == 'AzureBlobStorage':
        tantalus.tasks.transfer_file_server_azure_task.apply_async(args=(file_transfer.id,), queue=file_transfer.from_storage.get_transfer_queue_name())

    elif from_storage_type == 'AzureBlobStorage' and to_storage_type == 'ServerStorage':
        make_dirs_sig = tantalus.tasks.make_dirs_for_file_transfer_task.signature((file_transfer.id,), immutable=True)
        make_dirs_sig.set(queue=file_transfer.to_storage.get_mkdir_queue_name())
        transfer_file_sig = tantalus.tasks.transfer_file_azure_server_task.signature((file_transfer.id,), immutable=True)
        transfer_file_sig.set(queue=file_transfer.to_storage.get_transfer_queue_name())
        chain(make_dirs_sig, transfer_file_sig).apply_async()

    elif from_storage_type == 'ServerStorage' and to_storage_type == 'ServerStorage':
        make_dirs_sig = tantalus.tasks.make_dirs_for_file_transfer_task.signature((file_transfer.id,), immutable=True)
        make_dirs_sig.set(queue=file_transfer.to_storage.get_mkdir_queue_name())
        transfer_file_sig = tantalus.tasks.transfer_file_server_server_task.signature((file_transfer.id,), immutable=True)
        transfer_file_sig.set(queue=file_transfer.to_storage.get_transfer_queue_name())
        chain(make_dirs_sig, transfer_file_sig).apply_async()

    else:
        raise Exception('unsupported transfer')


def initialize_deployment(deployment):
    """
    Initialize a deployment.
    """
    if deployment.file_transfers.all().count() == 0:
        deployment.errors = False
        deployment.finished = True
        deployment.start = False
        deployment.running = False
    else:
        deployment.errors = False
        deployment.finished = False
        deployment.running = True
    deployment.save()


def start_file_transfers(deployment):
    """
    Start a set of file transfers.
    """
    for file_transfer in get_file_transfers_to_start(deployment):
        file_transfer.finished = False
        file_transfer.success = False
        file_transfer.state = ''
        file_transfer.message = ''
        file_transfer.save()
        start_file_transfer(file_transfer)


def read_excel_sheets(filename):
    """ 
    Load and read an excel file, extracting specific columns.
    """
    
    required_columns = ['sample_id']

    try:
        data = pd.read_excel(filename, sheetname=None)
    except IOError:
        raise ValueError('Unable to find file', filename)
    
    # convert all column names in the loaded file to lowercase
    for sheetname in data:
            data[sheetname].columns = [c.lower() for c in data[sheetname].columns]

    for sheetname in data:
        if set(required_columns).issubset(data[sheetname].columns):
            yield data[sheetname]


def start_md5_checks(file_instances):
    """
    Start md5 check jobs on file instances.
    """

    for file_instance in file_instances:
        md5_check = tantalus.models.MD5Check(
            file_instance=file_instance
        )
        md5_check.save()

        tantalus.tasks.check_md5_task.apply_async(args=(md5_check.id,), queue=file_instance.storage.get_md5_queue_name())


def file_instance_already_exists(file_resource, to_storage):
    """
    validate file instance on DESTINATION storage does not already exist
    """
    destination_file_instances = file_resource.fileinstance_set.filter(storage=to_storage)

    return len(destination_file_instances) >= 1


def validate_file_instance(file_resource, from_storage, error_type):
    """
    Validates the following:
    - if a file instance for the file resource exists on the SOURCE storage
            (ValidationError, do NOT proceed)
    - if there are multiple file instances for the file resource on the SOURCE storage
            (ValidationError, do NOT proceed)
    """
    source_file_instance = file_resource.fileinstance_set.filter(storage=from_storage)
    if len(source_file_instance) == 0:
        raise error_type(
            'file instance for file resource {} not deployed on source storage {}'.format(
                file_resource.filename, from_storage.name))

    # paranoia check - this if statement should never be able to run
    elif len(source_file_instance) > 1:
        raise error_type(
            'multiple file instances for file resource {} instances on {}'.format(file_resource.filename, from_storage))


def get_file_resources_from_datasets(datasets):
    """ generator function for getting file resources from datasets"""
    for dataset in datasets:
        file_resources = dataset.get_data_fileset()

        for file_resource in file_resources:
            yield file_resource


def validate_deployment(datasets, from_storage, to_storage, error_type):
    for file_resource in get_file_resources_from_datasets(datasets):
        validate_file_instance(file_resource, from_storage, error_type)

        existing_transfers = FileTransfer.objects.filter(
            file_instance__in=file_resource.fileinstance_set.all(),
            to_storage=to_storage)

        if len(existing_transfers) >= 1:
            if len(existing_transfers) > 1:
                raise error_type('multiple existing transfers for {} to {}'.format(file_resource.filename,
                                                                                   to_storage))


def count_num_transfers(datasets, to_storage):
    num_transfers = 0
    for file_resource in get_file_resources_from_datasets(datasets):
        destination_file_instances = file_resource.fileinstance_set.all().filter(storage=to_storage).count()
        if destination_file_instances == 0:
            num_transfers += 1
    return num_transfers


def add_file_transfers(deployment):
    """ creates the associated file transfer objects if necessary (ie. no existing file transfer), and returns the
        file transfer objects that should be started up again. """
    datasets = deployment.datasets.all()
    from_storage = deployment.from_storage
    to_storage = deployment.to_storage

    # Clear previous transfers, some of which may have completed successfully
    deployment.file_transfers.clear()

    for file_resource in get_file_resources_from_datasets(datasets):
        destination_file_instances = file_resource.fileinstance_set.filter(storage=to_storage)
        if len(destination_file_instances) >= 1:
            continue

        file_instance = file_resource.fileinstance_set.filter(storage=from_storage)[0]

        existing_transfers = FileTransfer.objects.filter(
            file_instance__in=file_resource.fileinstance_set.all(),
            to_storage=to_storage)

        if existing_transfers:
            file_transfer = existing_transfers[0]
        else:
            file_transfer = FileTransfer(
                from_storage=from_storage,
                to_storage=to_storage,
                file_instance=file_instance,
            )
            # TODO: add tests for the naming and transfer starting
            file_transfer.full_clean()
            file_transfer.save()

        deployment.file_transfers.add(file_transfer)


def get_file_transfers_to_start(deployment):
    for file_transfer in deployment.file_transfers.all():
        if not file_transfer.success:
            if file_transfer.finished: # existing file transfer that should be restarted
                yield file_transfer
            elif not(file_transfer.finished or file_transfer.running or file_transfer.success): # new file transfer
                yield file_transfer
            # TODO: see KRONOS-405
