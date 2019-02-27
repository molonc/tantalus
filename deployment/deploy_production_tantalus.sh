#!/bin/bash
set -v
cd /home/dalai/tantalus
git pull
source venv/bin/activate
pip3 install -r requirements.txt --ignore-installed
python manage.py migrate
touch tantalus/wsgi.py
exit