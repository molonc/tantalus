import django
import argparse

django.setup()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('primary_key')
    args = vars(parser.parse_args())
    return args


def run_task(id_, model, func):
    task_model = model.objects.get(pk=id_)

    if task_model.running:
        raise Exception('task already running')

    task_model.running = True
    task_model.finished = False
    task_model.success = False
    task_model.state = task_model.task_name.replace('_', ' ') + ' started'
    task_model.save()

    try:
        func(task_model)
    except:
        task_model.running = False
        task_model.finished = True
        task_model.success = False
        task_model.state = task_model.task_name.replace('_', ' ') + ' failed'
        task_model.save()
        raise

    task_model.running = False
    task_model.finished = True
    task_model.success = True
    task_model.state = task_model.task_name.replace('_', ' ') + ' finished'
    task_model.save()
