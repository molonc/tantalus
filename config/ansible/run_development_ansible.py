#!/usr/bin/env python

import sys
import os
import getpass

print 'username for the gsc'
username = raw_input()

print 'password for the gsc:'
password = getpass.getpass()

os.environ['GSC_API_PASSWORD'] = password

os.system('ansible-playbook playbook.yml -e "stashuser={}" -e "stashpassword={}" -i hosts.txt'.format(username, password))

