#!/usr/bin/env python

import sys
import os
import subprocess
import getpass

print 'username for the gsc'
username = raw_input()

print 'password for the gsc:'
password = getpass.getpass()

branch = subprocess.check_output('git rev-parse --abbrev-ref HEAD', shell=True).rstrip()

os.environ['GSC_API_PASSWORD'] = password
os.environ['TANTALUS_IS_PRODUCTION'] = "nope"

os.system('ansible-playbook playbook.yml -e "stashuser={}" -e "stashpassword={}" -e "stashversion={}" -i hosts.txt'.format(username, password, branch))

