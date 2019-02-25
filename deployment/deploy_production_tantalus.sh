#!/bin/bash

ssh -t ubuntu@40.85.254.93 <<EOF
  cd ~/tantalus
  git pull
  source venv/bin/activate
  pip3 install -r requirements.txt --ignore-installed
  python manage.py migrate
  touch tantalus/wsgi.py
  exit
EOF