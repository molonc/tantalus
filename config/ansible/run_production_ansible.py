#!/usr/bin/env python

import sys
import os
import getpass
import argparse

sys.path.append('/var/www/apps/tantalus/')

import tantalus.wsgi

parser = argparse.ArgumentParser()
parser.add_argument('--update_backend_only', action='store_true')
args = vars(parser.parse_args())

print 'password for stash:'
p = getpass.getpass()

command = 'ansible-playbook playbook.yml -e "mode=production" -e "stashuser=amcpherson" -e "stashpassword={}" -i hosts.txt'.format(p)
if args['update_backend_only']:
    command += ' --tags "backend"'

os.system(command)

