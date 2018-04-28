import django
import argparse
import errno

django.setup()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('primary_key')
    args = vars(parser.parse_args())
    return args


def run_task(id_, model, func):
    task_model = model.objects.get(pk=id_)

    temp_directory = os.path.join(django.conf.settings.TASK_LOG_DIRECTORY, task_model.task_name, str(id_))

    try:
        os.makedirs(temp_directory)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    if task_model.running:
        raise Exception('task already running')

    task_model.running = True
    task_model.finished = False
    task_model.success = False
    task_model.state = task_model.task_name.replace('_', ' ') + ' started'
    task_model.save()

    try:
        func(task_model, temp_directory)
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
