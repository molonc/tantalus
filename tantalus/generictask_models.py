"""GenericTask models and related functions."""

import json
import django.contrib.postgres.fields
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from tantalus.models import ServerStorage
from tantalus.generictask_script_utils import (
                            get_absolute_script_path_for_generic_task_type,
                            start_generic_task_instance,)


def return_gen_task_type_arg_default():
    """Essentially a lambda function that returns a dict.

    For technical reasons, we can't use a lambda function in the default
    to the JSON field for GenericTaskType above; but defining a function
    in the module scope works.
    """
    return {'arg1': None, 'arg2': 'default2'}


class GenericTaskType(models.Model):
    """A type of generic task you can perform.

    Comparing this with SimpleTask, the benefits of this are that you
    can run scripts with arbitrary parameters. The negatives are that
    you can't validate the attributes as well as with the SimpleTask
    structure.
    """
    # The name of the generic task type
    task_name = models.CharField(max_length=50,
                                 unique=True,
                                 help_text="The name of the task.")

    # The path of the script used by this generic task type relative to
    # the root of the generic task scripts directory.
    relative_script_path = models.CharField(
                          max_length=400,
                          help_text=(
                                "The path of the script used by this generic"
                                " task type (relative to the root of the"
                                " generic task scripts directory."))

    # What arguments the above script requires. Probably the easiest way
    # to use this field is to pass in a dictionary, and let's use that
    # as an example: (Though don't forget the versitility of this field;
    # see
    # https://docs.djangoproject.com/en/2.0/ref/contrib/postgres/fields/#django.contrib.postgres.fields.JSONField
    # for more details.)
    #
    # To specify the arguments that the above script requires, pass in a
    # dictionary with the argument names as keys and the None type as
    # their corresponding values. E.g.,
    #
    # {'arg1': None, 'arg2': None, 'arg3': None}
    #
    # Any argument not specified when creating an instance of this task
    # type will result in an exception being raised. If you want to
    # provide default values for the arguments such that the task
    # instances will take on the default argument values if they aren't
    # instantiated with the argument, then simply provide the defaults
    # as keys.  E.g., to give a default value to 'arg2', use
    #
    # {'arg1': None, 'arg2': 'default_val', 'arg3': None}
    required_and_default_args = django.contrib.postgres.fields.JSONField(
                                 verbose_name=(
                                     "script required arguments"
                                     " (see help text)"),
                                 default=return_gen_task_type_arg_default,
                                 help_text=(
                                     "The arguments that the task requires as"
                                     " a JSON object. Looking at the object as"
                                     " a dictionary, the keys are the argument"
                                     " names and the corresponding values are"
                                     " the default values for these arguments."
                                     " To specify an argument with no default"
                                     " value, simply use 'null' (without the"
                                     " quotes) as its value."),
                                 null=True,
                                 blank=True,)

    # The default host an instance of this task will run on unless
    # otherwise specified
    default_host = models.ForeignKey(ServerStorage,
                                     help_text=(
                                         "The default host an instance of"
                                         " this task will run on (unless"
                                         " otherwise specified)"),)

    def get_absolute_script_path(self):
        """Gets the absolute path to the script.

        The path location logic is defined in the module relating to
        running generictasks. The reason this method is exists is due to
        it needing to be called in a template.
        """
        return get_absolute_script_path_for_generic_task_type(self)

    def __str__(self):
        """String representation of the task type."""
        return "%s" % self.task_name


class GenericTaskInstance(models.Model):
    """An instance of a generic task type."""
    # The type of task that this is
    task_type = models.ForeignKey(GenericTaskType,
                                  help_text=("The generic task type of which"
                                             " this is an instance."))

    # What host the task is to be run on
    host = models.ForeignKey(ServerStorage,
                             help_text="The host on which the task will run.")

    # A name for the task instance
    instance_name = models.CharField(max_length=50,
                                     unique=True,
                                     help_text="The name for the instance.")

    # What arguments the script for this task should be called with.
    # These will be validated in the function
    # validate_generic_task_instance_args right after instantiating an
    # instance of the task.
    args = django.contrib.postgres.fields.JSONField(
                                default=dict,
                                null=True,
                                blank=True,
                                help_text=("The arguments to call the task"
                                           " type with as a JSON object."
                                           " The arguments must be a subset"
                                           " of the arguments required by the"
                                           " task type."))

    # Job state parameters. These variables conform to the SimpleTask
    # state representation structure.
    running = models.BooleanField(default=False)
    finished = models.BooleanField(default=False)
    success = models.BooleanField(default=False)
    stopping = models.BooleanField(default=False)
    state = models.TextField(blank=True)

    def get_queue_name(self):
        """Return the queue name.

        Only using 'db queues' for the forseeable future. The
        distinction between these types of queues and other is allegedly
        the number of workers assigned to the task.
        """
        return self.host.get_db_queue_name()

    def start_task(self):
        """Starts the task associated with a GenericTaskInstance."""
        # Start the job
        start_generic_task_instance.apply_async(
                args=(self.pk,),
                queue=self.get_queue_name())

    def dump_args_as_JSON_string(self):
        """Returns a string containing args as JSON."""
        return json.dumps(self.args)

    def __str__(self):
        """String representation of the task instance."""
        return "%s (type: %s)" % (self.instance_name,
                                  self.task_type.task_name)


@receiver(pre_save, sender=GenericTaskInstance)
def validate_generic_task_instance_args(instance, **_):
    """Validate a GenericTaskInstance against its task types.

    Check that each argument in the instance has the arguments required
    in the task type. If an argument in the instance is missing and a
    default exists in task type, then add in missing argument from the
    instance with the default from its task type; otherwise throw an
    exception

    This is called before each GenericTaskInstance is saved.

    Arg:
        instance: The GenericTaskInstance just about to be saved.
    Raises:
        A ValidationError exception if the instance fails to validate.
    """
    task_type_args_dict = instance.task_type.required_and_default_args
    task_instance_args_dict = instance.args

    # Confirm that the instance arguments is a subset of the task type
    # arguments
    if not set(task_instance_args_dict).issubset(set(task_type_args_dict)):
        # The task instance has unrecognized arguments
        raise ValidationError('Instance arguments are not a subset of the'
                              ' task type arguments!')

    # Now go through each argument from the type and make sure the
    # instance has a value
    for arg, value in task_type_args_dict.iteritems():
        if arg not in task_instance_args_dict.keys():
            # Argument is missing from instance. If the task type has a
            # default value use that; otherwise, raise an exception.
            if value:
                # Use the default provided by the task type
                task_instance_args_dict[arg] = value
            else:
                # Instance is missing required argument
                raise ValidationError('Instance is missing a value for'
                                      ' the "%s" argument' % arg)

    # Store any tacked on arguments to the instance
    instance.args = task_instance_args_dict


@receiver(post_save, sender=GenericTaskInstance)
def start_generic_task_on_create(instance, created, **_):
    """Starts the task associated with a GenericTaskInstance.

    This is called when a generic task is first saved (right after
    creation).
    """
    # Only trigger if the instance was just created
    if created:
        # Start the job
        instance.start_task()
