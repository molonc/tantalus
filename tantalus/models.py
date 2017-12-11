"""
Tantalus models
"""

from __future__ import unicode_literals

import os
import django
from django.db import models
from django.core.urlresolvers import reverse
import simple_history
from simple_history.models import HistoricalRecords
from polymorphic.models import PolymorphicModel


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


class Sample(models.Model):
    """
    Physical tumour or other tissue sample.
    """

    history = HistoricalRecords()

    sample_id = create_id_field(unique=True)

    def __unicode__(self):
        return self.sample_id

    def get_absolute_url(self):
        return reverse("sample-list")


class DNALibrary(models.Model):
    """
    DNA Library, possibly multiplexed.
    """

    history = HistoricalRecords()

    library_id = create_id_field(unique=True)

    EXOME = 'EXOME'
    WGS = 'WGS'
    RNASEQ = 'RNASEQ'
    SINGLE_CELL_WGS = 'SC_WGS'
    SINGLE_CELL_RNASEQ = 'SC_RNASEQ'
        
    library_type_choices = [
        (EXOME, 'Bulk Whole Exome Sequence'),
        (WGS, 'Bulk Whole Genome Sequence'),
        (RNASEQ, 'Bulk RNA-Seq'),
        (SINGLE_CELL_WGS, 'Single Cell Whole Genome Sequence'),
        (SINGLE_CELL_RNASEQ, 'Single Cell RNA-Seq'),
    ]

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


class DNASequences(models.Model):
    """
    Sequences of a DNA Library, possibly a subset of a multiplexed library.
    """

    history = HistoricalRecords()

    dna_library = models.ForeignKey(
        DNALibrary,
        on_delete=models.CASCADE,
    )

    index_sequence = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )

    sample = models.ForeignKey(
        Sample,
        on_delete=models.CASCADE,
    )

    def get_filename_index_sequence(self):
        if self.index_sequence == '':
            return 'N'
        else:
            return self.index_sequence

    class Meta:
        unique_together = ('dna_library', 'index_sequence')


class SequenceLane(models.Model):
    """
    Lane of Illumina Sequencing.
    """

    history = HistoricalRecords()

    flowcell_id = create_id_field()

    lane_number_choices = [('', '')] + [(str(a), str(a)) for a in range(1, 10)]

    lane_number = models.CharField(
        max_length=50,
        choices=lane_number_choices,
        blank=True,
    )

    GSC = 'GSC'
    BRC = 'BRC'

    sequencing_centre_choices = [
        (GSC, 'Genome Science Centre'),
        (BRC, 'Biomedical Research Centre'),
    ]

    sequencing_centre = models.CharField(
        max_length=50,
        choices=sequencing_centre_choices,
    )

    sequencing_library_id = create_id_field()

    sequencing_instrument = models.CharField(
        max_length=50,
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

    dna_library = models.ForeignKey(
        DNALibrary,
        on_delete=models.CASCADE,
    )

    def __unicode__(self):
        if self.lane_number == '':
            return '{}_{}'.format(self.sequencing_centre, self.flowcell_id)
        else:
            return '{}_{}_{}'.format(self.sequencing_centre, self.flowcell_id, self.lane_number)

    class Meta:
        unique_together = ('flowcell_id', 'lane_number')


class FileResource(models.Model):
    """
    Sequence data file.
    """

    history = HistoricalRecords()

    md5 = models.CharField(
        max_length=50,
        null=True,
        blank=True,
    )

    size = models.BigIntegerField()

    created = models.DateTimeField()

    BAM = 'BAM'
    BAI = 'BAI'
    FQ = 'FQ'

    file_type_choices = (
        (BAM, 'BAM'),
        (BAI, 'BAM Index'),
        (FQ, 'Fastq'),
    )

    file_type = models.CharField(
        max_length=50,
        choices=file_type_choices,
    )

    read_end = models.PositiveSmallIntegerField(
        null=True,
    )

    GZIP = 'GZIP'
    BZIP2 = 'BZIP2'
    UNCOMPRESSED = 'UNCOMPRESSED'

    compression_choices = (
        (GZIP, 'gzip'),
        (BZIP2, 'bzip2'),
        (UNCOMPRESSED, 'uncompressed'),
    )

    compression = models.CharField(
        max_length=50,
        choices=compression_choices,
    )

    filename = models.CharField(
        max_length=500,
        unique=True,
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
            self.UNCOMPRESSED: '',
        }[self.compression]


class AbstractDataSet(PolymorphicModel):
    """
    General Sequence Dataset.
    """

    history = HistoricalRecords()

    tags = models.ManyToManyField(Tag)

    lanes = models.ManyToManyField(
        SequenceLane,
        verbose_name='Lanes',
    )

    dna_sequences = models.ForeignKey(
        DNASequences,
        null=True,
        on_delete=models.SET_NULL,
    )

    def get_data_fileset(self):
        raise NotImplementedError()


class SingleEndFastqFile(AbstractDataSet):
    """
    Fastq file of single ended Illumina Sequencing.
    """

    history = HistoricalRecords()

    reads_file = models.OneToOneField(
        FileResource,
        on_delete=models.CASCADE,
        related_name='reads_file',
    )

    def __str__(self):
        return "SingleEndFastQ {}".format(self.id)

    def get_data_fileset(self):
        return [self.reads_file]


class PairedEndFastqFiles(AbstractDataSet):
    """
    Fastq file of paired ended Illumina Sequencing.
    """

    history = HistoricalRecords()

    reads_1_file = models.ForeignKey(
        FileResource,
        on_delete=models.CASCADE,
        related_name='reads_1_file',
    )

    reads_2_file = models.ForeignKey(
        FileResource,
        on_delete=models.CASCADE,
        related_name='reads_2_file',
    )

    def __str__(self):
        return "PairedEndFastq {}".format(self.id)

    def get_data_fileset(self):
        return [self.reads_1_file, self.reads_2_file]

    class Meta:
        unique_together = ('reads_1_file', 'reads_2_file')


class BamFile(AbstractDataSet):
    """
    Base class of bam files.
    """

    history = HistoricalRecords()

    HG19 = 'HG19'
    HG18 = 'HG18'
    UNALIGNED = 'UNALIGNED'
    UNUSABLE = 'UNUSABLE'

    reference_genome_choices = (
        (HG19, 'Human Genome 19'),
        (HG18, 'Human Genome 18'),
        (UNALIGNED, 'Not aligned to a reference'),
        (UNUSABLE, 'Alignments are not usable'),
    )

    reference_genome = models.CharField(
        max_length=50,
        choices=reference_genome_choices,
        default=UNALIGNED,
    )

    aligner = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        default=None,
    )

    bam_file = models.ForeignKey(
        FileResource,
        on_delete=models.CASCADE,
        related_name='bam_file',
    )

    bam_index_file = models.ForeignKey(
        FileResource,
        on_delete=models.CASCADE,
        related_name='bam_index_file',
    )

    def get_data_fileset(self):
        return [self.bam_file, self.bam_index_file]

    class Meta:
        unique_together = ('bam_file', 'bam_index_file')


class Storage(PolymorphicModel):
    """
    Details of a specific file storage location.
    """

    history = HistoricalRecords()

    name = models.CharField(
        max_length=50,
        unique=True,
    )

    def __unicode__(self):
        return '{}'.format(self.name)

    def get_filepath(self, file_resource):
        raise NotImplementedError()


class ServerStorage(Storage):
    """
    Server file storage for sequence data files.
    """

    history = HistoricalRecords()

    server_ip = models.CharField(
        max_length=50,
    )

    storage_directory = models.CharField(
        max_length=500,
    )

    username = models.CharField(
        max_length=30
    )

    queue_prefix = models.CharField(
        max_length=50
    )

    def get_storage_directory(self):
        # TODO: For read only storages ie gsc, this isnt necessary
        if not django.conf.settings.IS_PRODUCTION:
            return self.storage_directory.rstrip('/') + '_test'
        return self.storage_directory

    def get_transfer_queue_name(self):
        return self.queue_prefix + '.transfer'

    def get_md5_queue_name(self):
        return self.queue_prefix + '.md5'

    def get_db_queue_name(self):
        return self.queue_prefix + '.db'

    def get_filepath(self, file_resource):
        return os.path.join(
            str(self.get_storage_directory()),
            file_resource.filename.strip('/'))

    has_transfer_queue = True


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

    history = HistoricalRecords()

    storage_account = models.CharField(
        max_length=50,
    )

    storage_container = models.CharField(
        max_length=50,
    )

    credentials = models.ForeignKey(
        AzureBlobCredentials,
        on_delete=models.CASCADE,
    )

    def get_storage_container(self):
        if not django.conf.settings.IS_PRODUCTION:
            return self.storage_container + '-test'
        return self.storage_container

    def get_filepath(self, file_resource):
        # strip the slash, otherwise this creates an additional
        # <no name> root folder
        blobname = file_resource.filename.strip('/')
        blobpath = '/'.join([self.get_storage_container(), blobname])
        return blobpath

    has_transfer_queue = False


class FileInstance(models.Model):
    """
    Instance of a file in storage.
    """

    history = HistoricalRecords()

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

    running = models.BooleanField(default=False)
    finished = models.BooleanField(default=False)
    success = models.BooleanField(default=False)
    state = models.TextField(blank=True)
    message = models.TextField(blank=True)

    class Meta:
        abstract = True


class BRCFastqImport(SimpleTask):
    """
    When given an output dir + metadata, generate fastq files.
    """
    output_dir = models.CharField(
        max_length=500
    )
    storage = models.ForeignKey(
        ServerStorage,
        on_delete=models.CASCADE,
    )
    flowcell_id = models.CharField(
        max_length=50
    )


class FileTransfer(SimpleTask):
    """
    File transfer from one storage to another.
    """

    name = models.CharField(
        max_length=50,
        unique=True,
    )

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

    def get_transfer_queue_name(self):
        if self.to_storage.has_transfer_queue:
            return self.to_storage.get_transfer_queue_name()
        elif self.from_storage.has_transfer_queue:
            return self.from_storage.get_transfer_queue_name()
        else:
            raise Exception('no transfer queue for transfer')

    def get_absolute_url(self):
        return reverse("filetransfer-list")


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

    file_instance = models.ForeignKey(
        FileInstance,
    )


class GscWgsBamQuery(SimpleTask):
    """
    Query GSC API for WGS Bam data paths.
    """

    sample = models.ForeignKey(
        Sample,
    )


class GscDlpPairedFastqQuery(SimpleTask):
    """
    Query GSC API for DLP paired fastq data paths.
    """

    dlp_library_id = models.CharField(
        max_length=50,
        unique=True,
    )

    gsc_library_id = models.CharField(
        max_length=50,
        unique=True,
    )

