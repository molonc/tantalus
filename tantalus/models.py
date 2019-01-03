from __future__ import unicode_literals

import os
import django
import django.contrib.postgres.fields
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.urls import reverse
from django.core.validators import RegexValidator
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Max
from simple_history.models import HistoricalRecords
from polymorphic.models import PolymorphicModel
import account.models


def create_id_field(*args, **kwargs):
    return models.CharField(
        max_length=50,
        *args,
        **kwargs
    )


class Tag(models.Model):
    """
    Simple text tag associated with datasets.
    """

    history = HistoricalRecords()

    name = create_id_field(unique=True)

    def __unicode__(self):
        return self.name

    def count_datasets(self):
        """Count the number of datasets associated with this tag.

        For now I'm not including tagged analyses in this count.
        """
        sequence_dataset_count = self.sequencedataset_set.count()
        results_dataset_count = self.resultsdataset_set.count()

        return sequence_dataset_count + results_dataset_count

    def count_sequence_datasets(self):

        return self.sequencedataset_set.count()

    def count_result_datasets(self):

        return self.resultsdataset_set.count()

    def get_absolute_url(self):
        return reverse("tag-detail", args=(self.id,))


class Project(models.Model):
    """
    Project model
    """
    history = HistoricalRecords()

    name =  models.CharField(unique=True,max_length=255)

    def __str__(self):
        return self.name


class Patient(models.Model):

    """
    Patient model
    """
    SA_id = models.CharField(
        unique=True,
        max_length=120,
        null=True
    )

    reference_id = models.CharField(
        max_length=120,
        null=True,
    )

    external_patient_id = models.CharField(
        max_length=120,
        null=True
    )


    case_id = models.CharField(
        max_length=120,
        null=True
    )

    def get_absolute_url(self):
        return reverse("patient-list")

    def __str__(self):
        return self.SA_id


class Sample(models.Model):
    """
    Physical tumour or other tissue sample.
    """

    history = HistoricalRecords()

    sample_id = create_id_field(unique=True)

    external_sample_id = models.CharField(
        max_length=240,
        null=True,
        blank=True
    )

    submitter = models.CharField(
        max_length=240,
        null=True,
    )

    researcher = models.CharField(
        max_length=240,
        null=True,
    )

    tissue = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    note = models.TextField(
        null=True,
        blank=True
    )

    SA_id = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        null=True
    )

    projects = models.ManyToManyField(
        Project,
        blank=True,
    )

    def __str__(self):
        return self.sample_id

    def get_absolute_url(self):
        return reverse("sample-detail", args=(self.id,))

    def get_patient_name(self):
        return self.SA_id

    def get_submissions(self):
        return self.submission_set.all()


class LibraryType(models.Model):
    """
    Type of sequencing applied to a DNA library.
    """
    history = HistoricalRecords()

    name = models.CharField(
        max_length=50,
        blank=True,
        null=False,
        unique=True
    )

    description = models.CharField(
        max_length=240,
        blank=True,
        null=False,
        unique=True
    )

    def __unicode__(self):
        return self.name


class DNALibrary(models.Model):
    """
    DNA Library, possibly multiplexed.
    """

    history = HistoricalRecords()

    owner = models.ForeignKey(
        account.models.User,
        on_delete=models.SET_NULL,
        null=True,
    )

    library_id = create_id_field(unique=True)

    library_type = models.ForeignKey(
        LibraryType,
        on_delete=models.CASCADE,
        null=True
    )

    SINGLE_INDEX = 'S'
    DUAL_INDEX = 'D'
    NO_INDEXING = 'N'

    index_format_choices = (
        (SINGLE_INDEX, 'Single Index'),
        (DUAL_INDEX, 'Dual Index (i7 and i5)'),
        (NO_INDEXING, 'No Indexing')
    )

    index_format = models.CharField(
        max_length=50,
        choices=index_format_choices,
    )

    def __unicode__(self):
        return '{}_{}'.format(self.library_type, self.library_id)


class SequencingLane(models.Model):
    """
    Lane of Illumina Sequencing.
    """

    history = HistoricalRecords()

    owner = models.ForeignKey(
        account.models.User,
        on_delete=models.SET_NULL,
        null=True,
    )

    flowcell_id = create_id_field()

    lane_number_choices = [('', '')] + [(str(a), str(a)) for a in range(1, 10)]

    lane_number = models.CharField(
        max_length=50,
        choices=lane_number_choices,
        blank=True,
    )

    dna_library = models.ForeignKey(
        DNALibrary,
        on_delete=models.CASCADE,
    )

    GSC = 'GSC'
    BRC = 'BRC'

    sequencing_centre_choices = (
        (GSC, 'Genome Science Centre'),
        (BRC, 'Biomedical Research Centre'),
    )

    sequencing_centre = models.CharField(
        max_length=50,
        choices=sequencing_centre_choices,
    )

    sequencing_instrument = models.CharField(
        blank=True,
        null=True,
        max_length=50,
    )

    sequencing_library_id = create_id_field(
        null=True,
    )

    PAIRED = 'P'
    SINGLE = 'S'

    read_type_choices = (
        (PAIRED, 'Paired end tags'),
        (SINGLE, 'Single end tags')
    )

    read_type = models.CharField(
        max_length=50,
        choices=read_type_choices,
    )

    def __unicode__(self):
        if self.lane_number == '':
            return '{}_{}'.format(self.sequencing_centre, self.flowcell_id)
        else:
            return '{}_{}_{}'.format(self.sequencing_centre, self.flowcell_id, self.lane_number)

    class Meta:
        unique_together = ('flowcell_id', 'lane_number', 'dna_library')


class FileType(models.Model):
    """
    Type of a File Resource.
    """

    history = HistoricalRecords()

    name = models.CharField(
        unique=True,
        max_length=255,
    )

    extension = models.CharField(
        max_length=50,
        null=True,
        blank=True,
    )

    def __str__(self):
        """String representation of file type."""
        return "%s (%s)" % (self.name, self.extension)


class FileResource(models.Model):
    """
    File resource.
    """

    last_updated = models.DateTimeField(
        auto_now=True,
        help_text="When the file resource was last updated.",
    )

    history = HistoricalRecords()

    owner = models.ForeignKey(
        account.models.User,
        on_delete=models.SET_NULL,
        null=True,
    )

    md5 = models.CharField(
        max_length=50,
        null=True,
        blank=True,
    )

    size = models.BigIntegerField()

    created = models.DateTimeField()

    file_type = models.ForeignKey(
        FileType,
        null=True,
        on_delete=models.CASCADE,
    )

    GZIP = 'GZIP'
    BZIP2 = 'BZIP2'
    SPEC = 'SPEC'
    UNCOMPRESSED = 'UNCOMPRESSED'

    compression_choices = (
        (GZIP, 'gzip'),
        (BZIP2, 'bzip2'),
        (SPEC, 'SpEC'),
        (UNCOMPRESSED, 'uncompressed'),
    )

    compression = models.CharField(
        max_length=50,
        choices=compression_choices,
        default=UNCOMPRESSED,
    )

    filename = models.CharField(
        max_length=500,
        unique=True,
    )

    is_folder = models.BooleanField(
        default=False,
    )

    def __unicode__(self):
        return '{}'.format(self.md5)

    def get_filename_time(self):
        return self.created.strftime('%Y%m%d_%H%M%S')

    def get_filename_uid(self):
        return self.md5[:8]

    def get_compression_suffix(self):
        return {
            self.GZIP: '.gz',
            self.BZIP2: '.bz2',
            self.SPEC: '.spec',
            self.UNCOMPRESSED: '',
        }[self.compression]

    def get_file_size(self):
        size_mb = str("{:,}".format(self.size / 1000000)) + " MB"
        return size_mb


class SequenceFileInfo(models.Model):
    """
    Sequence data file.
    """

    history = HistoricalRecords()

    file_resource = models.OneToOneField(
        FileResource,
        on_delete=models.CASCADE,
    )

    owner = models.ForeignKey(
        account.models.User,
        on_delete=models.SET_NULL,
        null=True,
    )

    read_end = models.PositiveSmallIntegerField(
        null=True,
    )

    genome_region = models.TextField(
        null=True,
    )

    index_sequence = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )


class ReferenceGenome(models.Model):
    """
    Reference genome species / version.
    """

    history = HistoricalRecords()

    name = models.CharField(
        max_length=50,
        blank=True,
        null=False,
        unique=True
    )

    def __str__(self):
        return self.name


class AlignmentTool(models.Model):
    """
    Alignment tool used to create an aligned sequence dataset.
    """

    history = HistoricalRecords()

    name = models.CharField(
        unique=True,
        max_length=50,
    )

    description = models.CharField(
        max_length=250,
    )

    def __str__(self):
        return self.name


class SequenceDataset(models.Model):
    """
    Generalized dataset class.
    """

    history = HistoricalRecords()

    last_updated = models.DateTimeField(
        auto_now=True,
        help_text="When the dataset was last updated.",
    )

    owner = models.ForeignKey(
        account.models.User,
        on_delete=models.SET_NULL,
        null=True,
    )

    name = models.CharField(
        max_length=200,
        unique=True,
    )

    tags = models.ManyToManyField(
        Tag,
        blank=True,
    )

    BAM = 'BAM'
    FQ = 'FQ'

    dataset_type_choices = (
        (BAM, 'BAM Files'),
        (FQ, 'FastQ Files'),
    )

    dataset_type = models.CharField(
        max_length=50,
        choices=dataset_type_choices,
        null=False,
        default=BAM,
    )

    sample = models.ForeignKey(
        Sample,
        on_delete=models.CASCADE,
    )

    library = models.ForeignKey(
        DNALibrary,
        on_delete=models.CASCADE,
    )

    file_resources = models.ManyToManyField(
        FileResource,
    )

    sequence_lanes = models.ManyToManyField(
        SequencingLane,
    )

    analysis = models.ForeignKey(
        'Analysis',
        null=True,
        on_delete=models.CASCADE,
    )

    reference_genome = models.ForeignKey(
        ReferenceGenome,
        on_delete=models.CASCADE,
        null=True,
    )

    aligner = models.ForeignKey(
        'AlignmentTool',
        null=True,
    )

    def get_num_total_sequencing_lanes(self):
        return SequencingLane.objects.filter(dna_library=self.library).count()

    def get_is_complete(self):
        return self.sequence_lanes.all().count() == self.get_num_total_sequencing_lanes()

    def get_storage_names(self):
        return list(
            FileInstance.objects.filter(
                file_resource__sequencedataset=self)
            .values_list('storage__name', flat=True)
            .distinct())

    def get_dataset_type_name(self):
        return self.dataset_type

    def get_samples(self):
        return self.sample.sample_id

    def get_libraries(self):
        return self.library.library_id

    def get_library_type(self):
        return self.library.library_type

    def get_created_time(self):
        return self.file_resources.all().aggregate(Max('created'))['created__max']

    def get_absolute_url(self):
        return reverse("dataset-detail", args=(self.id,))

    def __str__(self):
        return self.name


# Validator for analysis version
analysis_version_validator = RegexValidator(
    regex=r"v\d+\.\d+\.\d+",
    message=' must be in "v<MAJOR>.<MINOR>.<PATCH>"; for example, "v0.0.1"',
)


class Analysis(models.Model):
    """
    Analysis/workflow details
    """

    history = HistoricalRecords()

    owner = models.ForeignKey(
        account.models.User,
        on_delete=models.SET_NULL,
        null=True,
    )

    name = models.CharField(
        max_length=200,
        unique=True,
    )

    version = models.CharField(
        max_length=200,
        validators=[analysis_version_validator,],
    )

    tags = models.ManyToManyField(
        Tag,
        blank=True,
    )

    jira_ticket = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )

    input_datasets = models.ManyToManyField(
        'SequenceDataset',
        related_name='inputdatasets',
        blank=True,
    )

    input_results = models.ManyToManyField(
        'ResultsDataset',
        related_name='inputresults',
        blank=True,
    )

    last_updated = models.DateTimeField(
        null=True,
        default=timezone.now,
    )

    status = models.CharField(
        max_length=50,
        blank=False,
        null=False,
        default="Unknown",
    )

    args = django.contrib.postgres.fields.JSONField(
        null=True,
        blank=True,
    )

    logs = models.ManyToManyField(
        FileResource,
        blank=True,
    )

    def __unicode__(self):
        return '{}'.format(self.name)

    def get_absolute_url(self):
        return reverse("analysis-detail", args=(self.id,))


class ResultsDataset(models.Model):
    """
    Generalized results class.
    """

    history = HistoricalRecords()

    owner = models.ForeignKey(
        account.models.User,
        on_delete=models.SET_NULL,
        null=True,
    )

    name = models.CharField(
        max_length=200,
        unique=True,
    )

    tags = models.ManyToManyField(
        Tag,
        blank=True,
    )

    results_type = models.CharField(
        max_length=50,
        null=False,
    )

    results_version = models.CharField(
        max_length=50,
        null=False,
    )

    analysis = models.ForeignKey(
        Analysis,
        null=True,
        on_delete=models.SET_NULL,
    )

    samples = models.ManyToManyField(
        Sample,
    )

    file_resources = models.ManyToManyField(
        FileResource,
    )

    def get_absolute_url(self):
        return reverse("result-detail", args=(self.id,))

    def __unicode__(self):
        return '{}'.format(self.name)


class Storage(PolymorphicModel):
    """
    Details of a specific file storage location.
    """

    history = HistoricalRecords()

    owner = models.ForeignKey(
        account.models.User,
        on_delete=models.SET_NULL,
        null=True,
    )

    name = models.CharField(
        max_length=50,
        unique=True,
    )

    def __unicode__(self):
        return '{}'.format(self.name)

    def get_filepath(self, file_resource):
        raise NotImplementedError()

    @property
    def is_read_only(self):
        return False


class ServerStorage(Storage):
    """
    Server file storage for sequence data files.
    """

    storage_type = 'server'

    history = HistoricalRecords()

    server_ip = models.CharField(
        max_length=50,
    )

    storage_directory = models.CharField(
        max_length=500,
    )

    username = models.CharField(
        max_length=30,
    )

    read_only = models.BooleanField(
        default=True,
    )

    def get_prefix(self):
        return self.storage_directory

    def get_filepath(self, file_resource):
        return os.path.join(
            str(self.storage_directory),
            file_resource.filename.strip('/'))

    @property
    def is_read_only(self):
        return self.read_only

    storage_type = 'server'


class AzureBlobStorage(Storage):
    """
    Azure blob storage for sequence files.
    """

    storage_type = 'blob'

    history = HistoricalRecords()

    # The max length for the CharField of the storage account and
    # container name match the name contraints imposed by Azure, at
    # least as of 2018-05-30
    storage_account = models.CharField(
        max_length=24,
    )

    storage_container = models.CharField(
        max_length=63,
    )

    def get_prefix(self):
        return '/'.join([self.storage_account, self.storage_container])

    def get_filepath(self, file_resource):
        # strip the slash, otherwise this creates an additional
        # <no name> root folder
        blobname = file_resource.filename.strip('/')
        blobpath = '/'.join([self.storage_account, self.storage_container, blobname])
        return blobpath

    storage_type = 'blob'


class FileInstance(models.Model):
    """
    Instance of a file in storage.
    """

    history = HistoricalRecords()

    owner = models.ForeignKey(
        account.models.User,
        on_delete=models.SET_NULL,
        null=True,
    )

    storage = models.ForeignKey(
        Storage,
        on_delete=models.CASCADE,
    )

    file_resource = models.ForeignKey(
        FileResource,
        on_delete=models.CASCADE,
    )

    is_deleted = models.BooleanField(
        default=False,
    )

    def get_filepath(self):
        return self.storage.get_filepath(self.file_resource)

    class Meta:
        unique_together = ('file_resource', 'storage')


class Sow(models.Model):
    """
    Sow model
    """
    # Unique on name
    name = models.CharField(max_length=50,unique=True)

    def __str__(self):
        return self.name

class Submission(models.Model):
    """
    Submission model
    """
    # Add nullable library id
    sample = models.ForeignKey(
        Sample,
        on_delete=models.CASCADE,
        null=True
    )

    sow = models.ForeignKey(
        Sow,
        on_delete=models.CASCADE,
        null=True
    )

    submission_date = models.CharField(max_length=255,null=True)

    submitted_by = models.CharField(max_length=50)

    lanes_sequenced = models.IntegerField(
        blank=True,
        null=True
    )

    coverage = models.IntegerField(
        default=0
    )

    updated_goal = models.IntegerField(
        blank=True,
        null=True
    )

    payment = models.CharField(
        max_length=50,
        blank=True
    )

    data_path = models.CharField(
        max_length=240,
        blank=True,
        null=True,
        default=None
    )

    library_type = models.ForeignKey(
        LibraryType,
        on_delete=models.CASCADE,
        null=True
    )

    def get_absolute_url(self):
        return reverse("submissions-list")
