from __future__ import absolute_import

from celery import shared_task, Task
from tantalus.models import Transfer
import time


@shared_task
def run_transfer(pk):
    print 'sleeping'
    time.sleep(5)
    print 'finished'
    transfer = Transfer.objects.get(pk=pk)
    transfer.state = 'Finished'
    transfer.result = 100
    transfer.save()
    return 100
