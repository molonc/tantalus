#!/usr/bin/env python

import sys
import os
import subprocess
import getpass
import socket
import errno

print 'username for the gsc'
username = raw_input()

print 'password for the gsc:'
password = getpass.getpass()

branch = subprocess.check_output('git rev-parse --abbrev-ref HEAD', shell=True).rstrip()

os.environ['GSC_API_PASSWORD'] = password
os.environ['TANTALUS_IS_PRODUCTION'] = "nope"

logs_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'tmp', 'logs'))

try:
    os.makedirs(logs_dir)
except OSError as e:
    if e.errno != errno.EEXIST:
        raise

os.environ['TASK_LOG_DIRECTORY'] = logs_dir
os.environ['TASK_LOG_USERNAME'] = os.environ['USER']
os.environ['TASK_LOG_HOSTNAME'] = socket.gethostname()

os.system('ansible-playbook playbook.yml -e "stashuser={}" -e "stashpassword={}" -e "stashversion={}" -i hosts.txt'.format(username, password, branch))

