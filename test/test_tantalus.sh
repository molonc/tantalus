#!/bin/bash
set -v
cd /home/ubuntu/tantalus
git pull
source venv/bin/activate
pip3 install -r requirements.txt --ignore-installed
python manage.py migrate