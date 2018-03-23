from __future__ import absolute_import

import os
import sys
import errno
import django
from celery import shared_task, Task
import tantalus.models
import tantalus.file_transfer_utils
import tantalus.gsc_queries
import subprocess
import traceback
import tantalus.import_brc_fastqs


def simple_task_wrapper(id_, model, func, name):
    task_model = model.objects.get(pk=id_)

    if task_model.running:
        return

    task_log_name = name.replace(' ', '_').lower()
    log_dir = os.path.join(django.conf.settings.TASK_LOG_DIRECTORY, task_log_name, str(id_))

    try:
        os.makedirs(log_dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    stdout_filename = os.path.join(log_dir, 'stdout.txt')
    stderr_filename = os.path.join(log_dir, 'stderr.txt')

    task_model.running = True
    task_model.finished = False
    task_model.success = False
    task_model.state = name + ' started'
    task_model.message = ''
    task_model.save()

    with open(stdout_filename, 'a', 0) as stdout_file, open(stderr_filename, 'a', 0) as stderr_file:
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = stdout_file, stderr_file
        try:
            func(task_model)
        except Exception as e:
            sys.stderr.write(traceback.format_exc())
            error_message = str(e) + '\n' + traceback.format_exc()
            task_model.running = False
            task_model.finished = True
            task_model.success = False
            task_model.state = name + ' failed'
            task_model.message = error_message
            task_model.save()
            raise
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr

    task_model.running = False
    task_model.finished = True
    task_model.success = True
    task_model.state = name + ' finished'
    task_model.save()


@shared_task
def transfer_files_task(file_transfer_id):
    simple_task_wrapper(
        id_=file_transfer_id,
        model=tantalus.models.FileTransfer,
        func=tantalus.file_transfer_utils.transfer_files,
        name='transfer files',
    )


@shared_task
def check_md5_task(md5_check_id):
    simple_task_wrapper(
        id_=md5_check_id,
        model=tantalus.models.MD5Check,
        func=tantalus.file_transfer_utils.check_or_update_md5,
        name='check or update md5',
    )


@shared_task
def query_gsc_wgs_bams_task(query_id):
    simple_task_wrapper(
        id_=query_id,
        model=tantalus.models.GscWgsBamQuery,
        func=tantalus.gsc_queries.query_gsc_wgs_bams,
        name='query GSC for WGS BAMs',
    )


@shared_task
def query_gsc_dlp_paired_fastqs_task(query_id):
    simple_task_wrapper(
        id_=query_id,
        model=tantalus.models.GscDlpPairedFastqQuery,
        func=tantalus.gsc_queries.query_gsc_dlp_paired_fastqs,
        name='query GSC for DLP fastqs',
    )


@shared_task
def import_brc_fastqs_task(query_id):
    simple_task_wrapper(
        id_=query_id,
        model=tantalus.models.BRCFastqImport,
        func=tantalus.import_brc_fastqs.load_brc_fastqs,
        name='import brc fastqs into tantalus',
    )
