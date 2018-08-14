import collections

import tantalus.backend.utils


def fastq_paired_end_check(file_info):
    """ Check for paired ends for a set of fastq files """

    # Check for each read end
    pair_check = collections.defaultdict(set)
    for info in file_info:
        if len(info['sequence_lanes']) > 1:
            raise Exception('more than 1 lane for fastqs not yet supported')

        fastq_id = (
            info['library_id'],
            info['index_sequence'],
            info['sequence_lanes'][0]['flowcell_id'],
            info['sequence_lanes'][0]['lane_number'],
        )

        if info['read_end'] in pair_check[fastq_id]:
            raise Exception('duplicate fastq file with end {} for {}'.format(
                info['read_end'], fastq_id))

        pair_check[fastq_id].add(info['read_end'])

    for fastq_id, pair_info in pair_check.iteritems():
        for read_end in (1, 2):
            if read_end not in pair_info:
                raise Exception('missing fastq file with end {} for {}'.format(
                    read_end, fastq_id))


def create_sequence_dataset_models(file_info, storage_name):
    """ Create tantalus sequence models for a list of files """ 

    json_list = []

    storage = dict(
        name=storage_name,
    )

    # Sort files by dataset
    dataset_info = collections.defaultdict(list)
    for info in file_info:
        dataset_name = '{}-{}-{}-{} ({})'.format(
            info['dataset_type'],
            info['sample_id'],
            info['library_type'],
            info['library_id'],
            tantalus.backend.utils.get_lanes_str(info['sequence_lanes']),
        )
        dataset_info[dataset_name].append(info)

    # Create datasets
    for dataset_name, infos in dataset_info.iteritems():
        sample = dict(
            sample_id=infos[0]['sample_id'],
        )

        library = dict(
            library_id=infos[0]['library_id'],
            library_type=infos[0]['library_type'],
            index_format=infos[0]['index_format'],
        )

        sequence_dataset = dict(
            name=dataset_name,
            dataset_type=infos[0]['dataset_type'],
            sample=sample,
            library=library,
            sequence_lanes=[],
            file_resources=[],
            model='SequenceDataset',
        )

        for info in infos:
            # Check consistency for fields used for dataset
            check_fields = (
                'dataset_type',
                'sample_id',
                'library_id',
                'library_type',
                'index_format',
            )
            for field_name in check_fields:
                if info[field_name] != infos[0][field_name]:
                    raise Exception('error with field {}'.format(field_name))

            for sequence_lane in info['sequence_lanes']:
                sequence_lane = dict(sequence_lane)
                sequence_lane['dna_library'] = library
                sequence_dataset['sequence_lanes'].append(sequence_lane)

            sequence_file_info = dict(
                index_sequence=info['index_sequence'],
            )

            if 'read_end' in info:
                sequence_file_info['read_end'] = info['read_end']

            file_resource = dict(
                size=info['size'],
                created=info['created'],
                file_type=info['file_type'],
                compression=info['compression'],
                filename=info['filename'],
                sequencefileinfo=sequence_file_info,
            )

            sequence_dataset['file_resources'].append(file_resource)

            file_instance = dict(
                storage=storage,
                file_resource=file_resource,
                model='FileInstance',
            )

            if 'filename_override' in info:
                file_instance['filename_override'] = info['filename_override']

            json_list.append(file_instance)

        json_list.append(sequence_dataset)

    return json_list
