#!/bin/bash
set -v
cd /home/dalai/tantalus
git fetch origin
git reset --hard origin/master
source venv/bin/activate
pip3 install -r requirements.txt --ignore-installed
python3 manage.py migrate
sudo systemctl restart emperor.uwsgi.service
exit
