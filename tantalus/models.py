"""
Tantalus models
"""

from __future__ import unicode_literals

from django.db import models
import taggit.models
import simple_history
from simple_history.models import HistoricalRecords
from taggit.managers import TaggableManager
from polymorphic.models import PolymorphicModel

simple_history.register(taggit.models.Tag)


def create_id_field(*args, **kwargs):
    return models.CharField(
        max_length=50,
        *args,
        **kwargs
    )


class Sample(models.Model):
    """
    Physical tumour or other tissue sample.
    """

    history = HistoricalRecords()

    APARICIO = 'SA'
    HUNTSMAN = 'DG'
    OTHER = 'O'

    sample_id_space_choices = (
        (APARICIO, 'Aparicio'),
        (HUNTSMAN, 'Huntsman'),
        (OTHER, 'Other'),
    )

    sample_id_space = models.CharField(
        max_length=50,
        choices=sample_id_space_choices,
    )

    sample_id = create_id_field(unique=True)

    def __unicode__(self):
        return '{}_{}'.format(self.sample_id_space, self.sample_id)


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

    lane_number = models.PositiveSmallIntegerField()

    sequencing_centre = create_id_field()

    sequencing_library_id = create_id_field()

    sequencing_instrument_choices = (
        ('HX', 'HiSeqX'),
        ('H2500', 'HiSeq2500'),
        ('N550', 'NextSeq550'),
        ('MI', 'MiSeq'),
        ('O', 'other'),
    )

    sequencing_instrument = models.CharField(
        max_length=50,
        choices=sequencing_instrument_choices,
    )

    read_type_choices = (
        ('P', 'PET'),
        ('S', 'SET')
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

    tags = TaggableManager()
    history = HistoricalRecords()

    lanes = models.ManyToManyField(
        SequenceLane,
        verbose_name='Lanes',
    )
    
    dna_sequences = models.ForeignKey(
        DNASequences,
        on_delete=models.CASCADE,
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

    reference_genome_choices = (
        ('hg19','Human Genome 19'),
        ('hg18','Human Genome 18'),
        ('none','Unaligned'),
    )

    reference_genome = models.CharField(
        max_length=50,
        choices=reference_genome_choices,
    )

    aligner = models.CharField(
        max_length=50,
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

    storage_key = models.CharField(
        max_length=200,
    )


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

    class Meta:
        unique_together = ('file_resource', 'storage')


class FileTransfer(models.Model):
    """
    Transfer of a specific data file.
    """

    from_storage = models.ForeignKey(
        Storage,
        related_name='file_transfer_from_storage',
    )

    to_storage = models.ForeignKey(
        Storage,
        related_name='file_transfer_to_storage',
    )

    file_instance = models.ForeignKey(
        FileInstance,
    )

    new_filename = models.CharField(
        max_length=500,
    )

    progress = models.FloatField(
        default=0.,
    )

    error_messages = models.TextField(
        blank=True,
    )

    running = models.BooleanField('Running', default=False)
    finished = models.BooleanField('Finished', default=False)
    success = models.BooleanField('Success', default=False)

    class Meta:
        unique_together = ('from_storage', 'to_storage', 'file_instance')


class GSCQuery(models.Model):
    """
    Query GSC API for data paths.
    """

    samples = models.ManyToManyField(
        Sample,
    )

    exception_message = models.CharField(
        max_length=1000,
    )

    running = models.BooleanField('Running', default=False)
    finished = models.BooleanField('Finished', default=False)
    success = models.BooleanField('Success', default=False)


class Deployment(models.Model):
    """
    Deployment from one storage to another.
    """

    from_storage = models.ForeignKey(
        Storage,
        related_name='deployment_from_storage',
    )

    to_storage = models.ForeignKey(
        Storage,
        related_name='deployment_to_storage',
    )

    datasets = models.ManyToManyField(
        AbstractDataSet,
    )

    file_transfers = models.ManyToManyField(
        FileTransfer,
        blank=True,
    )

    running = models.BooleanField('Running', default=False)
    finished = models.BooleanField('Finished', default=False)
    errors = models.BooleanField('Errors', default=False)
