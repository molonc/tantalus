from __future__ import absolute_import

from celery import shared_task, Task
import tantalus.models
import tantalus.file_transfer_utils
import tantalus.gsc_queries
import subprocess
import traceback


def simple_task_wrapper(id_, model, func, name, is_last=True):
    task_model = model.objects.get(pk=id_)
    task_model.running = True
    task_model.finished = False
    task_model.success = False
    task_model.state = name + ' started'
    task_model.message = ''
    task_model.save()

    try:
        func(task_model)
    except Exception as e:
        error_message = str(e) + '\n' + traceback.format_exc()
        task_model.running = False
        task_model.finished = True
        task_model.success = False
        task_model.state = name + ' failed'
        task_model.message = error_message
        task_model.save()
        raise

    if is_last:
        task_model.running = False
        task_model.finished = True
        task_model.success = True

    task_model.state = name + ' finished'
    task_model.save()


@shared_task
def make_dirs_for_file_transfer_task(transfer_file_id):
    simple_task_wrapper(
        id_=transfer_file_id,
        model=tantalus.models.FileTransfer,
        func=tantalus.file_transfer_utils.make_dirs_for_file_transfer,
        name='make directories',
        is_last=False,
    )


@shared_task
def transfer_file_server_azure_task(transfer_file_id):
    simple_task_wrapper(
        id_=transfer_file_id,
        model=tantalus.models.FileTransfer,
        func=tantalus.file_transfer_utils.transfer_file_server_azure,
        name='transfer file',
    )


@shared_task
def transfer_file_azure_server_task(transfer_file_id):
    simple_task_wrapper(
        id_=transfer_file_id,
        model=tantalus.models.FileTransfer,
        func=tantalus.file_transfer_utils.transfer_file_azure_server,
        name='transfer file',
    )


@shared_task
def transfer_file_server_server_task(transfer_file_id):
    simple_task_wrapper(
        id_=transfer_file_id,
        model=tantalus.models.FileTransfer,
        func=tantalus.file_transfer_utils.transfer_file_server_server,
        name='transfer file',
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
        model=tantalus.models.QueryGscWgsBams,
        func=tantalus.gsc_queries.query_gsc_wgs_bams,
        name='query GSC for WGS BAMs',
    )


@shared_task
def query_gsc_dlp_paired_fastqs_task(query_id):
    simple_task_wrapper(
        id_=query_id,
        model=tantalus.models.QueryGscDlpPairedFastqs,
        func=tantalus.gsc_queries.query_gsc_dlp_paired_fastqs,
        name='query GSC for WGS BAMs',
    )

