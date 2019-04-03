#!/bin/bash
set -v
cd /home/ubuntu/tantalus
git fetch origin
git reset --hard origin/master
source venv/bin/activate
/home/ubuntu/tantalus/venv/bin/python /home/ubuntu/tantalus/backups/get_backups.py
sudo -u postgres psql -c "SELECT pg_terminate_backend (pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = 'tantalus'"
sudo -u postgres psql -c "DROP database tantalus"
sudo -u postgres psql -c "CREATE database tantalus"
pg_restore -h localhost -p 5432 -U tantalus -d tantalus < /home/ubuntu/tantalus/backups/daily_backup.dump
pip3 install -r requirements.txt --ignore-installed
python manage.py migrate
