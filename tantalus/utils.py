from tantalus.models import FileTransfer, SequenceDataFile
from tasks import transfer_file


def get_default_filename(dataset, seq_data_file):
    """
    Get the default filename of the given sequence data file and the dataset it belongs too
    :param dataset: SequenceDataset object
    :param seq_data_file: SequenceDataFile object that needs to be named
    :return: filename string in UNIX
    """

    filetype = dataset.__class__.__name__

    id = seq_data_file.id
    if filetype == 'PairedEndFastqFiles':
        if id == dataset.reads_1_file.id:
            return dataset.default_reads_1_filename()
        elif id == dataset.reads_2_file.id:
            return dataset.default_reads_2_filename()
        else:
            #TODO: is this exception needed?
            raise Exception("ERROR: This model instance of SequenceDataset with pk: {} is corrupted - please notify database admin").format(pk=dataset.id)

    elif filetype == 'BamFile':
        if id == dataset.bam_file.id:
            return dataset.default_bam_filename()
        elif id == dataset.bam_index_file.id:
            return dataset.default_bam_index_filename()
        else:
            #TODO: is this exception needed?
            raise Exception("ERROR: This model instance of SequenceDataset with pk: {} is corrupted - please notify database admin").format(pk=dataset.id)

    elif filetype == 'SingleEndFastqFile':
        if id == dataset.reads_file.id:
            return dataset.default_reads_filename()
        else:
            raise Exception("ERROR: This model instance of SequenceDataset with pk: {} is corrupted - please notify database admin").format(pk=dataset.id)

    else:
        # TODO: is this exception needed?
        raise Exception('Unsupported default naming for file')



def start_transfers(deployment):
    """ Start a set of transfers for a deployment.
    """

    # get all SequenceDatasets related to this deployment
    for dataset in deployment.datasets.all():
        seq_data_files = dataset.get_data_fileset()

        #for each sequencedatafile in the SequenceDataset
        for seq_data_file in seq_data_files:
            file_instances = seq_data_file.fileinstance_set.filter(storage=deployment.to_storage)

            if len(file_instances) >= 1:
                raise ValueError('seq data {} already deployed on {}'.format(seq_data_files, deployment.to_storage))

            file_instances = seq_data_file.fileinstance_set.filter(storage=deployment.from_storage)

            if len(file_instances) == 0:
                raise ValueError('seq data {} not deployed on {}'.format(seq_data_files, deployment.from_storage))

            elif len(file_instances) > 1:
                raise ValueError('multiple seq data {} instances on {}'.format(seq_data_files, deployment.from_storage))

            # TODO: pick an ideal file instance to transfer from, rather than arbitrarily?
            file_instance = file_instances[0]

            # filter for any existing transfers involving any 1 of the file_instances for this file resource
            existing_transfers = FileTransfer.objects.filter(
                file_instance__in=file_instances,
                deployment__to_storage=deployment.to_storage)

            if len(existing_transfers) > 1:
                raise ValueError('multiple existing transfers for {} to {}'.format(seq_data_files, deployment.to_storage))

            elif len(existing_transfers) == 1:
                file_transfer = existing_transfers[0]

            else:
                file_transfer = FileTransfer()
                file_transfer.from_storage = deployment.from_storage
                file_transfer.to_storage = deployment.to_storage
                file_transfer.file_instance = file_instance
                #TODO: add tests for the naming and transfer starting
                file_transfer.new_filename = get_default_filename(dataset, seq_data_file)
                file_transfer.save()

                transfer_file.apply_async(args=(file_transfer.id,), queue=deployment.from_storage.name)

            deployment.file_transfers.add(file_transfer)


