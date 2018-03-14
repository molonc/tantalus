from __future__ import absolute_import

import os
import errno
import subprocess
import time
import signal
import django
import tantalus.models
from celery import shared_task


def simple_task_wrapper(id_, model):
    log_dir = os.path.join(django.conf.settings.TASK_LOG_DIRECTORY, model.task_name, str(id_))

    try:
        os.makedirs(log_dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    stdout_filename = os.path.join(log_dir, 'stdout.txt')
    stderr_filename = os.path.join(log_dir, 'stderr.txt')

    with open(stdout_filename, 'a', 0) as stdout_file, open(stderr_filename, 'a', 0) as stderr_file:
        script = os.path.join(django.conf.settings.BASE_DIR, 'tantalus', 'backend', 'task_scripts', model.task_name + '.py')

        task = subprocess.Popen(['python', '-u', script, str(id_)], stdout=stdout_file, stderr=stderr_file)

        stdout_file.write('!! Started task process with id {} !!\n'.format(task.pid))
        stderr_file.write('!! Started task process with id {} !!\n'.format(task.pid))

        while task.poll() is None:
            time.sleep(10)

            if model.objects.get(pk=id_).stopping == True:
                stderr_file.write('!! Sending interrupt to task process !!\n')
                task.send_signal(signal.SIGINT)
                time.sleep(60)

                if task.poll() is None:
                    stderr_file.write('!! Sending kill to task process !!\n')
                    task.kill()

                model_instance = model.objects.get(pk=id_)
                model_instance.stopping = False
                model_instance.running = False
                model_instance.finished = True
                model_instance.save()

        stdout_file.write('!! Finished task process with id {} !!\n'.format(task.pid))
        stderr_file.write('!! Finished task process with id {} !!\n'.format(task.pid))


@shared_task
def transfer_files_task(file_transfer_id):
    simple_task_wrapper(
        id_=file_transfer_id,
        model=tantalus.models.FileTransfer,
    )


@shared_task
def check_md5_task(md5_check_id):
    simple_task_wrapper(
        id_=md5_check_id,
        model=tantalus.models.MD5Check,
    )


@shared_task
def query_gsc_wgs_bams_task(query_id):
    simple_task_wrapper(
        id_=query_id,
        model=tantalus.models.GscWgsBamQuery,
    )


@shared_task
def query_gsc_dlp_paired_fastqs_task(query_id):
    simple_task_wrapper(
        id_=query_id,
        model=tantalus.models.GscDlpPairedFastqQuery,
    )


@shared_task
def import_brc_fastqs_task(query_id):
    simple_task_wrapper(
        id_=query_id,
        model=tantalus.models.BRCFastqImport,
    )


@shared_task
def import_dlp_bams_task(query_id):
    simple_task_wrapper(
        id_=query_id,
        model=tantalus.models.ImportDlpBam,
    )
