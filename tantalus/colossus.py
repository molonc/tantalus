import django
import requests

def get_colossus_sublibraries_from_library_id(library_id):
    """
    Gets the sublibrary information from a library id
    :return: results for a sublibrary query
    """
    sublibraries = []
    sublibrary_url = '{}sublibraries/?library__pool_id={}'.format(django.conf.settings.COLOSSUS_API_URL, library_id)

    while sublibrary_url is not None:
        r = requests.get(sublibrary_url)

        if r.status_code != 200:
            raise Exception('Returned {}: {}'.format(r.status_code, r.reason))

        if len(r.json()['results']) == 0:
            raise Exception('No sublibrary results for {}'.format(sublibrary_url))

        sublibraries.extend(r.json()['results'])

        if 'next' in r.json():
            sublibrary_url = r.json()['next']
        else:
            sublibrary_url = None

    return sublibraries

def query_libraries_by_library_id(library_id):
    library_url = '{}library/?pool_id={}'.format(django.conf.settings.COLOSSUS_API_URL, library_id)

    r = requests.get(library_url)

    if r.status_code != 200:
        raise Exception('Returned {}: {}'.format(r.status_code, r.reason))

    results = r.json()['results']

    if len(results) == 0:
        raise Exception('No entries for library {}'.format(library_id))

    if len(results) > 1:
        raise Exception('Multiple entries for library {}'.format(library_id))

    return results[0]

