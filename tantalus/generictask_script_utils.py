"""Functions for running scripts associated with GenericTasks."""

import errno
import json
import os
import signal
import subprocess
import time
import celery
import django.conf
import tantalus.generictask_models


def get_absolute_script_path_for_generic_task_type(task_type=None):
    """Gets the absolute script path for a generic task type.

    The path is
    $DJANGO_BASE_DIR/tantalus/backend/generic_task_scripts/script.py. If
    this function is called without a task type, then it simply returns
    the directory that contains all of the scripts
    (generic_task_scripts/).
    """
    if task_type:
        # Return the script path
        return os.path.join(django.conf.settings.BASE_DIR,
                            'tantalus',
                            'backend',
                            'generic_task_scripts',
                            task_type.relative_script_path)

    # Return the directory path
    return os.path.join(django.conf.settings.BASE_DIR,
                        'tantalus',
                        'backend',
                        'generic_task_scripts')


def get_log_path_for_generic_task_instance(instance, logfile=None):
    """Gets the log path for a generic task intance.

    The path is $TASK_LOG_DIRECTORY/task_type/instance_pk/{logfile}.txt.
    If logfile is None or an empty string, then this function returns
    the log directory path.
    """
    # Escape the task name
    escaped_task_name = instance.task_type.task_name.replace(" ", "-")

    # Get path for log directory
    log_dir = os.path.join(django.conf.settings.TASK_LOG_DIRECTORY,
                           escaped_task_name,
                           str(instance.pk),)

    if logfile:
        # Return the specific log file path
        return os.path.join(log_dir, logfile + '.txt')

    # Return the log directory path
    return log_dir


def get_all_relative_script_paths():
    """Gets the relative paths of all scripts in script directory.

    Returns a list of the relative script paths as strings.
    """
    # Get the script directory
    script_dir = get_absolute_script_path_for_generic_task_type()

    # Get the character length of the script directory in a
    # representation where it has a trailing slash
    root_len = (len(script_dir) if script_dir.endswith('/')
                                            else len(script_dir) + 1)

    # Collect the script names
    script_paths = []

    for dirpath, dirnames, filenames in os.walk(script_dir):
        for filename in filenames:
            # Add the script path but don't include the root path
            script_paths.append(os.path.join(dirpath[root_len:], filename))

    return script_paths


@celery.shared_task
def start_generic_task_instance(instance_pk):
    """Start and manage a generic task instance.

    This is different from the Simple Task structure in that *all* of
    the Django processing of the script is done in this function. The
    scripts in the generic task scripts directory have no knowledge of
    and access to django.

    Here the script is run with its sole argument being a JSON string
    which contains all of the argument names and their values.
    """
    # Get the instance corresponding to the pk passed in
    instance = tantalus.generictask_models.GenericTaskInstance.objects.get(
                                                                pk=instance_pk)

    # Get the log directory, and create it if it doesn't exist
    log_dir = get_log_path_for_generic_task_instance(instance)

    try:
        # Make the directory
        os.makedirs(log_dir)
    except OSError as e:
        # Only allow exceptions raised due to the directory already
        # existing; otherwise, pass along the original exception.
        if e.errno != errno.EEXIST:
            raise

    # File paths for stdout and stderr
    stdout_filename = get_log_path_for_generic_task_instance(instance,
                                                             'stdout')
    stderr_filename = get_log_path_for_generic_task_instance(instance,
                                                             'stderr')

    # Start the script
    with open(stdout_filename, 'a', 0) as stdout_file,\
         open(stderr_filename, 'a', 0) as stderr_file:

        # Get the script path
        script_path = get_absolute_script_path_for_generic_task_type(
                                                            instance.task_type)

        # Start the task
        task = subprocess.Popen(['python',
                                 '-u',                  # force unbuffered output
                                 script_path,           # script path
                                 json.dumps(instance.args),     # args
                                ],
                                stdout=stdout_file,
                                stderr=stderr_file)

        # Set the task's job management state to indicate that it's
        # running
        instance.running = True
        instance.finished = False
        instance.success = False
        instance.state = instance.task_type.task_name + ' started'
        instance.save()

        # Write a start message to both stdout and stderr
        start_message = "!! Started task process with id {} !!\n".format(task.pid)
        stdout_file.write(start_message)
        stderr_file.write(start_message)

        # Listen for a return code or stop signals every 10 seconds
        # while the task is in progress
        finished = False

        while not finished:
            # Wait a bit
            time.sleep(10)

            # Get the return code if one exists
            return_code = task.poll()

            # Find out whether our job is finished. If it is, update the
            # job state variables and break out of this loop
            if return_code is not None:
                # Job's done
                instance.running = False
                instance.finished = True

                if return_code is 0:
                    # The job was successful
                    instance.success = True
                    instance.state = instance.task_type.task_name + ' succesful'
                else:
                    # The job failed
                    instance.state = instance.task_type.task_name + ' failed'

                # Save the instance
                instance.save()

                # Get out of the loop
                finished = True
            elif instance.stopping:
                # Stop message received. Ask the job nicely to stop and
                # give it a minute to do so.
                stderr_file.write("!! Sending interrupt to task process !!\n")
                task.send_signal(signal.SIGINT)
                time.sleep(60)

                # Make sure the job is complete
                return_code_new = task.poll()

                if return_code_new is None:
                    # The job is still running and has either ignored
                    # our request to stop or is taking to long. Kill the
                    # task.
                    stderr_file.write("!! Sending kill to task process !!\n")
                    task.kill()

                # Update job state variables
                instance.stopping = False
                instance.running = False
                instance.finished = True
                instance.save()

                # Get out of the loop
                finished = True

        # Write a completion message to both stdout and stderr
        done_message = "!! Finished task process with id {} !!\n".format(task.pid)
        stdout_file.write(done_message)
        stderr_file.write(done_message)
