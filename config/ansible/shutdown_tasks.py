import sys
import django
sys.path.append('/var/www/apps/tantalus/')
import tantalus.wsgi
django.setup()
from tantalus.models import *

for model in (FileTransfer, GscDlpPairedFastqQuery, GscWgsBamQuery, MD5Check,):
    for instance in model.objects.filter(running=True):
        print model.__name__, instance.id
        instance.running = False
        instance.finished = True
        instance.save()



