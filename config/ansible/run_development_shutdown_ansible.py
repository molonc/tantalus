#!/usr/bin/env python

import os

os.system('ansible-playbook playbook.yml --tags shutdown -i hosts.txt')

