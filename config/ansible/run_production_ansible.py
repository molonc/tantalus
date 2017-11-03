#!/usr/bin/env python

import sys
import os
import getpass

sys.path.append('/var/www/apps/tantalus/')

import tantalus.wsgi

print 'password for stash:'
p = getpass.getpass()

os.system('ansible-playbook playbook.yml -e "mode=production" -e "stashuser=amcpherson" -e "stashpassword={}" -i hosts.txt'.format(p))

