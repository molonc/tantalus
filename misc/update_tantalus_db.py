"""
Loading new data into Tantalus from Colossus REST API

See Colossus REST API documentation here:
https://www.bcgsc.ca/wiki/display/MO/Colossus+Documentation
"""


import requests
import sys
import os
import django

sys.path.append('./')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tantalus.settings')
django.setup()

from tantalus.models import *

# HOSTNAME='http://127.0.0.1:8000/api/'
HOSTNAME='http://colossus.bcgsc.ca/api/'
JSON_FORMAT='?format=json'
DEFAULT_LIBRARY_TYPE=DNALibrary.SINGLE_CELL_WGS
INDEX_FORMAT=DNALibrary.DUAL_INDEX #Data coming from colossus should all be dual indexed


def get_json(resource_name):
    r = requests.get('{hostname}{resource}{format}'.format(
        hostname=HOSTNAME, resource=resource_name, format=JSON_FORMAT)
    )
    # r.raise_for_status() #check if request is successful?
    if r.status_code != 200:
        raise Exception('Returned {}: {}'.format(r.status_code, r.reason))

    try:
        r = r.json()
        if len(r) == 0:
            raise Exception('No entries for {}'.format(resource_name))
    except ValueError: #invalid json returned
        raise Exception('Unable to parse response into JSON')
    finally:
        return r


def get_json_with_filter(resource_name, filter_string):
    r = requests.get('{hostname}{resource}{format}&{filter_string}'.format(
        hostname=HOSTNAME, resource=resource_name, format=JSON_FORMAT, filter_string=filter_string)
    )

    if r.status_code != 200:
        raise Exception('Returned {}: {}'.format(r.status_code, r.reason))

    try:
        r = r.json()
        if len(r) == 0:
            raise Exception('No entries for {}'.format(resource_name))

    except ValueError: #invalid json returned
        raise Exception('Unable to parse response into JSON')

    finally:
        return r


def get_difference(tantalus, colossus):
    """
    get difference between lists of items in both databases

    NOTE: This must be a list of UNIQUE IDs that is found in BOTH databases
    eg. for Samples, sample_id is a unique identifier
    """

    tantalus = set(tantalus)
    colossus = set(colossus)
    to_add = colossus - tantalus
    to_delete = tantalus - colossus
    return to_add, to_delete


def add_new_samples(samples):
    """ takes in a list of sample id strings and creates new sample objects in tantalus"""

    for sample in samples:
        print "ADDING this sample: {}".format(sample)
        s = Sample()
        s.sample_id = sample
        s.save()


def delete_samples(samples):
    for sample_id in samples:
        print "DELETING this sample: {}".format(sample_id)
        s = Sample.objects.filter(sample_id=sample_id)
        s.delete()


def add_new_libraries(libs):
    for lib in libs:
        l, created = DNALibrary.objects.get_or_create(
            library_id=lib,
            library_type=DEFAULT_LIBRARY_TYPE,
            index_format=INDEX_FORMAT)
        print "ADDING this library: {}".format(lib)

        if created:
            update_tantalus_dnasequences(lib)


def delete_libraries(libs):
    for lib in libs:
        print "DELETING this library: {}".format(lib)
        l = DNALibrary.objects.filter(
            library_id=lib,
            library_type=DEFAULT_LIBRARY_TYPE,
            index_format=INDEX_FORMAT)
        l.delete()


def add_new_sequencelanes(seqs):
    """

    :param seqs: a list of sequence flowcell_ids that will be added to tantalus
    :return: void
    """
    json_colossus_sequencelanes = get_json('sequencing')

    flowcell_map = {}
    for j in json_colossus_sequencelanes:
        for lane in j['lane_set']:
            flowcell_map[lane['flow_cell_id']] = j

    for seq in seqs:
        ## no flow cell or lane for this seq - don't add this
        if seq == "":
            print "no flowcell or lane"

        else:
            sequencelane = SequenceLane()
            sequencelane.flowcell_id = seq.split('_')[0]
            sequencelane.sequencing_centre = flowcell_map[seq]['sequencingdetail']['sequencing_center']
            sequencelane.sequencing_instrument = flowcell_map[seq]['sequencing_instrument']
            sequencelane.read_type = flowcell_map[seq]['read_type']
            sequencelane.index_read_type = flowcell_map[seq]['index_read_type']
            if flowcell_map[seq]['sequencingdetail']['sequencing_center'] == 'BCCAGSC':
                sequencelane.sequencing_library_id = flowcell_map[seq]['sequencingdetail']['gsc_library_id']
            if '_' in seq:
                sequencelane.lane_number = seq.split('_')[1]
            sequencelane.dna_library = DNALibrary.objects.get(library_id=flowcell_map[seq]['library'])
            sequencelane.save()


def delete_sequencelanes(seqs, seq_lib_map):
    pass


def add_new_sublibs(sublibs, library_id):
    for sublib in sublibs:
        # the foreign key name is sample_id, and the name of the field inside sample is also sample_id, which is why this key is accessed twice
        sample_id = sublib['sample_id']['sample_id']
        sample = Sample.objects.get(sample_id=sample_id)
        library = DNALibrary.objects.get(library_id=library_id)

        s, created = DNASequences.objects.get_or_create(
            sample = sample,
            dna_library = DNALibrary.objects.get(library_id=library_id)
        )

        # TODO: ask andrew whether reverse complement is needed or not
        if library.index_format == DNALibrary.DUAL_INDEX:
            s.index_sequence = "{i7}-{i5}".format(
                i7=sublib['primer_i7'],
                i5=sublib['primer_i5']
            )
            s.save()

        else:
            raise Exception('One or more sublibraries for library {} are not dual indexed, '
                            'colossus data should be dual indexed. Contact database admin.'.format(library))


def update_tantalus_samples():

    tantalus_samples = Sample.objects.values_list('sample_id')
    json_colossus_samples = get_json('sample')
    colossus_samples = [j['sample_id'] for j in json_colossus_samples]

    samples_to_add, samples_to_delete = get_difference(tantalus_samples, colossus_samples)
    add_new_samples(samples_to_add)
    delete_samples(samples_to_delete)


def update_tantalus_DNAlibrary():
    tantalus_libs = DNALibrary.objects.values_list('library_id', flat=True)
    json_colossus_libs = get_json('library')
    colossus_libs = [j['pool_id'] for j in json_colossus_libs]

    libraries_to_add, libraries_to_delete = get_difference(tantalus_libs, colossus_libs)
    add_new_libraries(libraries_to_add)
    delete_libraries(libraries_to_delete)


def update_tantalus_sequencelane():

    ## parsing sequence flowcell and lane number together so that it is queryable in the colossus database
    tantalus_sequencelanes = SequenceLane.objects.values_list('flowcell_id', 'lane_number')
    tantalus_sequencelanes = [(seq[0] + seq[1]) for seq in tantalus_sequencelanes]

    json_colossus_sequencelanes = get_json('sequencing')
    colossus_sequencelanes = [j['sequencingdetail']['flow_cell_id'] for j in json_colossus_sequencelanes]

    # creating a map of flowcell ids to library id
    sequence_library_map = {j['sequencingdetail']['flow_cell_id']: j['library']
                            for j in json_colossus_sequencelanes}

    sequences_to_add, sequences_to_delete = get_difference(tantalus_sequencelanes, colossus_sequencelanes)
    add_new_sequencelanes(sequences_to_add)
    delete_sequencelanes(sequences_to_delete, sequence_library_map)


def update_tantalus_dnasequences(library):
    # called in add_new_libraries, is passed a library pool id

    ## TODO: how to check if sublibrary information has changed if library hasnt - Exceptional case?
    ## TODO: ASSUME THAT ALL SUBLIBRARY INFORMATION IS NEW BECAUSE THE LIBRARY IS NEW
    filter_string = "pool_id={}".format(library)
    json_library = get_json_with_filter('library', filter_string)

    # there should only be one library for this filter
    if len(json_library)==1:
        sublibrary_set = json_library[0]['sublibraryinformation_set']
        add_new_sublibs(sublibrary_set, library)
    else:
        raise Exception('This library identifier is not unique.. Returned more than one library. Please ensure uniqueness of library ID')


def update_tantalus():
    update_tantalus_samples()
    update_tantalus_DNAlibrary()  #calls update_tantalus_dnasequences inside as well
    update_tantalus_sequencelane()


if __name__ == '__main__':
    DNALibrary.objects.all().delete()


    delete_samples(['SA928'])
    delete_libraries(['A90652A'])

    add_new_samples(['SA928'])
    add_new_libraries(['A90652A'])
    add_new_sequencelanes(['CB95TANXX_6'])









