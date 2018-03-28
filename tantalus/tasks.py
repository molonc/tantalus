from __future__ import absolute_import

import os
import errno
import subprocess
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
        script = os.path.join(django.conf.settings.BASE_DIR, 'tantalus', 'backend', 'scripts', model.task_name + '.py')
        subprocess.check_call(['python', '-u', script, str(id_)], stdout=stdout_file, stderr=stderr_file)


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
