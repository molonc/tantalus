from __future__ import unicode_literals

import os
import django
import django.contrib.postgres.fields
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.core.urlresolvers import reverse
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


class Project(models.Model):
    """
    Project model
    """
    history = HistoricalRecords()

    name =  models.CharField(unique=True,max_length=255)

    def __unicode__(self):
        return self.name


class Patient(models.Model):

    """
    Patient model
    """
    patient_id = models.CharField(
        unique=True,
        max_length=120,
        null=True
    )

    external_patient_id = models.CharField(
        unique=True,
        max_length=120,
        null=True
    )


    def get_absolute_url(self):
        return reverse("patient-list")

    def __str__(self):
        return self.patient_id


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

    collaborator = models.CharField(
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

    patient_id = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        null=True
    )

    projects = models.ManyToManyField(
        Project,
        blank=True,
    )

    def __unicode__(self):
        return self.sample_id

    def get_absolute_url(self):
        return reverse("sample-list")

    def get_patient_name(self):
        return self.patient_id

    def get_submissions(self):
        return self.submission_set.all()


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

    EXOME = 'EXOME'
    WGS = 'WGS'
    RNASEQ = 'RNASEQ'
    SINGLE_CELL_WGS = 'SC_WGS'
    SINGLE_CELL_RNASEQ = 'SC_RNASEQ'
    EXCAP = 'EXCAP'
    BISULFITE = 'BISULFITE'
    CHIP = 'CHIP'
    MRE = 'MRE'
    MIRNA = 'MIRNA'
    MEDIP = 'MEDIP'
    DNA_AMPLICON = 'DNA_AMPLICON'

    library_type_choices = (
        (EXOME, 'Bulk Whole Exome Sequence'),
        (WGS, 'Bulk Whole Genome Sequence'),
        (RNASEQ, 'Bulk RNA-Seq'),
        (SINGLE_CELL_WGS, 'Single Cell Whole Genome Sequence'),
        (SINGLE_CELL_RNASEQ, 'Single Cell RNA-Seq'),
        (EXCAP,'Exon Capture'),
        (MIRNA,'micro RNA'),
        (BISULFITE,'Bisulfite'),
        (CHIP,'Chromatin Immunoprecipitation'),
        (MRE,'Methylation sensitive restriction enzyme sequencing'),
        (MEDIP,'Methylated DNA immunoprecipitation'),
        (DNA_AMPLICON,'Targetted DNA Amplicon Sequence')
    )

    library_type = models.CharField(
        max_length=50,
        choices=library_type_choices,
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
    Lookup table for the SequenceDataset.reference_genome field
    """

    history = HistoricalRecords()

    #HG19 = 'HG19'
    #HG18 = 'HG18'
    #MM10 = 'MM10'
    #UNALIGNED = 'UNALIGNED'
    #UNUSABLE = 'UNUSABLE'
    #
    #reference_genome_choices = (
    #    (HG19, 'Human Genome 19'),
    #    (HG18, 'Human Genome 18'),
    #    (MM10, 'Mouse Genome 10'),
    #    (UNALIGNED, 'Not aligned to a reference'),
    #    (UNUSABLE, 'Alignments are not usable'),
    #)

    reference_genome = models.CharField(
        max_length=50,
        null=True,
        unique=True,
        #default=UNALIGNED, #not necessary
    )


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
    )

    library = models.ForeignKey(
        DNALibrary,
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
    )

    HG19 = 'HG19'
    HG18 = 'HG18'
    MM10 = 'MM10'
    UNALIGNED = 'UNALIGNED'
    UNUSABLE = 'UNUSABLE'

    reference_genome_choices = (
        (HG19, 'Human Genome 19'),
        (HG18, 'Human Genome 18'),
        (MM10, 'Mouse Genome 10'),
        (UNALIGNED, 'Not aligned to a reference'),
        (UNUSABLE, 'Alignments are not usable'),
    )

    #temp = models.CharField(
    #    max_length=50,
    #    # TODO: foreign key or update choices
    #    #choices=reference_genome_choices,
    #    default=UNALIGNED,
    #)

    reference_genome = models.ForeignKey(
        ReferenceGenome,
        on_delete=models.CASCADE,
        null=True,
    )

    aligner = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        default=None,
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
        null=False,
    )

    samples = models.ManyToManyField(
        Sample,
    )

    file_resources = models.ManyToManyField(
        FileResource,
    )

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

    queue_prefix = models.CharField(
        max_length=50,
    )

    read_only = models.BooleanField(
        default=True,
    )

    def get_prefix(self):
        return self.storage_directory

    def get_md5_queue_name(self):
        return self.queue_prefix + '.md5'

    def get_db_queue_name(self):
        return self.queue_prefix + '.db'

    def get_filepath(self, file_resource):
        return os.path.join(
            str(self.storage_directory),
            file_resource.filename.strip('/'))

    @property
    def is_read_only(self):
        return self.read_only

    has_transfer_queue = True

    storage_type = 'server'


class AzureBlobCredentials(models.Model):
    """
    Azure blob credentials.
    """

    history = HistoricalRecords()

    storage_key = models.CharField(
        max_length=200,
    )


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

    credentials = models.ForeignKey(
        AzureBlobCredentials,
        on_delete=models.CASCADE,
    )

    def get_prefix(self):
        return '/'.join([self.storage_account, self.storage_container])

    def get_filepath(self, file_resource):
        # strip the slash, otherwise this creates an additional
        # <no name> root folder
        blobname = file_resource.filename.strip('/')
        blobpath = '/'.join([self.storage_account, self.storage_container, blobname])
        return blobpath

    has_transfer_queue = False

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

    filename_override = models.CharField(
        max_length=500,
        blank=True,
        default='',
    )

    def get_filepath(self):
        if self.filename_override is not '':
            return self.filename_override

        return self.storage.get_filepath(self.file_resource)

    class Meta:
        unique_together = ('file_resource', 'storage')


class SimpleTask(models.Model):
    """
    Base model for task run with celery.
    """

    name = models.CharField(
        max_length=50,
        unique=False,
    )

    running = models.BooleanField(default=False)
    finished = models.BooleanField(default=False)
    success = models.BooleanField(default=False)
    stopping = models.BooleanField(default=False)
    state = models.TextField(blank=True)

    def get_queue_name(self):
        raise NotImplementedError()

    def get_absolute_url(self):
        return reverse(self.view)

    class Meta:
        abstract = True


class BRCFastqImport(SimpleTask):
    """
    When given an output dir + metadata, generate fastq files.
    """

    view = 'brcfastqimport-list'

    task_name = 'import_brc_fastqs_into_tantalus'

    output_dir = models.CharField(
        max_length=500,
    )

    storage = models.ForeignKey(
        ServerStorage,
        on_delete=models.CASCADE,
    )

    flowcell_id = models.CharField(
        max_length=50,
    )

    def get_queue_name(self):
        return self.storage.get_db_queue_name()


class FileTransfer(SimpleTask):
    """
    File transfer from one storage to another.
    """

    view = 'filetransfer-list'

    task_name = 'transfer_files'

    tag_name = models.CharField(
        max_length=50,
    )

    from_storage = models.ForeignKey(
        Storage,
        related_name='filetransfer_from_storage',
    )

    to_storage = models.ForeignKey(
        Storage,
        related_name='filetransfer_to_storage',
    )

    def get_count_total(self):
        return SequenceDataset.objects.filter(tags__name=self.tag_name).count()

    def get_count_finished(self):
        return SequenceDataset.objects.filter(tags__name=self.tag_name, file_resources__fileinstance__storage=self.to_storage).distinct().count()

    def get_queue_name(self):
        if self.to_storage.has_transfer_queue:
            return self.to_storage.queue_prefix + '.transfer'
        elif self.from_storage.has_transfer_queue:
            return self.from_storage.queue_prefix + '.transfer'
        else:
            # Use Shahlab for default Azure-Azure transfer queue
            return ServerStorage.objects.get(name='shahlab').queue_prefix + '.transfer'

    def __unicode__(self):
        return self.name


class ReservedFileInstance(models.Model):
    """
    Lock on specific file instance being transferred to.
    """

    file_resource = models.ForeignKey(
        FileResource,
        on_delete=models.CASCADE,
    )

    to_storage = models.ForeignKey(
        Storage,
        on_delete=models.CASCADE,
    )

    file_transfer = models.ForeignKey(
        FileTransfer,
        on_delete=models.CASCADE,
    )

    class Meta:
        unique_together = ('file_resource', 'to_storage')


class MD5Check(SimpleTask):
    """
    Check of set MD5 task.
    """

    task_name = 'check_or_update_md5'

    file_instance = models.ForeignKey(
        FileInstance,
    )


class GscWgsBamQuery(SimpleTask):
    """
    Query GSC API for WGS Bam data paths.
    """

    view = 'gscwgsbamquery-list'

    task_name = 'query_gsc_for_wgs_bams'

    library_ids = django.contrib.postgres.fields.ArrayField(
        models.CharField(max_length=50),
    )

    skip_file_import = models.BooleanField(
        default=False,
    )

    skip_older_than = models.DateTimeField(
        default=None,
        blank=True,
        null=True,
    )

    tag_name = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )

    def get_queue_name(self):
        return get_object_or_404(ServerStorage, name='gsc').get_db_queue_name()


class GscDlpPairedFastqQuery(SimpleTask):
    """
    Query GSC API for DLP paired fastq data paths.
    """

    view = 'gscdlppairedfastqquery-list'

    task_name = 'query_gsc_for_dlp_fastqs'

    dlp_library_id = models.CharField(
        max_length=50,
        unique=True,
    )

    gsc_library_id = models.CharField(
        max_length=50,
        unique=True,
    )

    def get_queue_name(self):
        return get_object_or_404(ServerStorage, name='gsc').get_db_queue_name()


class ImportDlpBam(SimpleTask):
    """
    Import BAMs from DLP pipeline.
    """

    view = 'importdlpbam-list'

    task_name = 'import_dlp_bams'

    storage = models.ForeignKey(
        Storage,
    )

    bam_paths = django.contrib.postgres.fields.ArrayField(
        models.CharField(max_length=500),
    )

    def get_queue_name(self):
        if self.storage.has_transfer_queue:
            return self.storage.get_db_queue_name()
        else:
            return get_object_or_404(ServerStorage, name='shahlab').get_db_queue_name()


class Sow(models.Model):
    """
    Sow model
    """
    # Unique on name
    name = models.CharField(max_length=50,unique=True)

    def __unicode__(self):
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

    EXOME = 'EXOME'
    WGS = 'WGS'
    RNASEQ = 'RNASEQ'
    SINGLE_CELL_WGS = 'SC_WGS'
    SINGLE_CELL_RNASEQ = 'SC_RNASEQ'
    EXCAP = 'EXCAP'
    BISULFITE = 'BISULFITE'
    CHIP = 'CHIP'
    MRE = 'MRE'
    MIRNA = 'MIRNA'
    MEDIP = 'MEDIP'
    DNA_AMPLICON = 'DNA_AMPLICON'

    library_type_choices = (
        (EXOME, 'Bulk Whole Exome Sequence'),
        (WGS, 'Bulk Whole Genome Sequence'),
        (RNASEQ, 'Bulk RNA-Seq'),
        (SINGLE_CELL_WGS, 'Single Cell Whole Genome Sequence'),
        (SINGLE_CELL_RNASEQ, 'Single Cell RNA-Seq'),
        (EXCAP,'Exon Capture'),
        (MIRNA,'micro RNA'),
        (BISULFITE,'Bisulfite'),
        (CHIP,'Chromatin Immunoprecipitation'),
        (MRE,'Methylation sensitive restriction enzyme sequencing'),
        (MEDIP,'Methylated DNA immunoprecipitation'),
        (DNA_AMPLICON,'Targetted DNA Amplicon Sequence')
    )

    library_type = models.CharField(
        max_length=240,
        blank=True,
        null=True,
        default=None,
        choices=library_type_choices
    )

    def get_absolute_url(self):
        return reverse("submissions-list")
