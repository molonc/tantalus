#!/usr/bin/env python

import sys
import os
import getpass

print 'username for stash'
username = raw_input()

print 'password for stash:'
password = getpass.getpass()

os.system('ansible-playbook playbook.yml -e "stashuser={}" -e "stashpassword={}" -i hosts.txt'.format(username, password))

