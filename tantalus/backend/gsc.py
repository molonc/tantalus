import os
import requests


class GSCAPI(object):
    def __init__(self):
        """
        Create a session object, authenticating based on the tantalus user.
        """

        self.request_handle = requests.Session()

        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        self.gsc_api_url = os.environ.get('GSC_API_URL', 'http://sbs:8100/')

        create_session_url = os.path.join(self.gsc_api_url, 'session')
        auth_json = {
            'username': os.environ.get('GSC_API_USERNAME'),
            'password': os.environ.get('GSC_API_PASSWORD'),
        }

        # TODO: prompt for username and password if none are provided
        response = self.request_handle.post(create_session_url, json=auth_json, headers=self.headers)

        if response.status_code == 200:
            # Add the authentication token to the headers.
            token = response.json().get('token')
            self.headers.update({'X-Token': token})
        else:
            raise Exception('unable to authenticate GSC API')

    def query(self, query_string):
        """
        Query the gsc api.
        """
        
        query_url = self.gsc_api_url + query_string
        result = self.request_handle.get(query_url, headers=self.headers).json()

        if 'status' in result and result['status'] == 'error':
            raise Exception(result['errors'])

        return result


raw_instrument_map = {
    'HiSeq': 'HiSeq2500',
    'HiSeqX': 'HiSeqX',
    'NextSeq': 'NextSeq550',
}


def get_sequencing_instrument(machine):
    """
    Sequencing instrument decode.
    Example machines are HiSeq-27 or HiSeqX-2.
    """
    
    raw_instrument = machine.split('-')[0]
    return raw_instrument_map[raw_instrument]


