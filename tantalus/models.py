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


def create_id_field(name, *args, **kwargs):
    return models.CharField(
        name,
        max_length=50,
        blank=False,
        null=False,
        *args,
        **kwargs
    )


class Sample(models.Model):
    """
    Physical tumour or other tissue sample.
    """

    history = HistoricalRecords()

    sample_id_space_choices = (
        ('SA','Aparicio'),
        ('DG','Huntsman'),
        ('O','Other'),
    )

    sample_id_space = models.CharField(
        'Sample ID Space',
        max_length=50,
        blank=False,
        null=False,
        choices=sample_id_space_choices,
    )

    sample_id = create_id_field('Sample ID',
                                unique=True,
                                )


    def __unicode__(self):
        return '{}_{}'.format(self.sample_id_space, self.sample_id)


class SequenceDataFile(models.Model):
    """
    Sequence data file.
    """

    history = HistoricalRecords()

    md5 = models.CharField(
        'MD5',
        max_length=50,
        blank=False,
        null=False,
        unique=True,
    )

    size = models.BigIntegerField(
        'Size',
        null=False,
    )

    created = models.DateTimeField(
        'Created',
        null=False,
    )

    file_type_choices = (
        ('BAM', 'BAM'),
        ('BAI', 'BAM Index'),
        ('FQ', 'Fastq'),
    )

    file_type = models.CharField(
        'Type',
        max_length=50,
        blank=False,
        null=False,
        choices=file_type_choices,
    )

    compression_choices = (
        ('gzip', 'gzip'),
        ('bzip2', 'bzip2'),
        ('none', 'none'),
    )

    compression = models.CharField(
        'Compression',
        max_length=50,
        blank=False,
        null=False,
        choices=compression_choices,
    )

    default_filename = models.CharField(
        'Default Filename',
        max_length=500,
        blank=False,
        null=False,
    )

    def __unicode__(self):
        return '{}'.format(self.md5)

    def get_filename_time(self):
        return self.created.strftime('%Y%m%d_%H%M%S')

    def get_filename_uid(self):
        return self.md5[:8]

    def get_compression_suffix(self):
        return {
            'gzip': '.gz',
            'bzip2': '.bz2',
            'none': '',
        }[self.compression]


class DNALibrary(models.Model):
    """
    DNA Library, possibly multiplexed.
    """

    history = HistoricalRecords()

    library_id = create_id_field('Library ID', unique=True)

    library_type_choices = [
        ('exome', 'Bulk Whole Exome Sequence'),
        ('wgs', 'Bulk Whole Genome Sequence'),
        ('sc_wgs', 'Single Cell Whole Genome Sequence'),
        ('rnaseq', 'Bulk RNA-Seq'),
        ('sc_rnaseq', 'Single Cell RNA-Seq'),
    ]

    library_type = models.CharField(
        'Library Type',
        max_length=50,
        blank=False,
        null=False,
        choices=library_type_choices,
    )

    index_format_choices = (
        ('D', 'Dual Index (i7 and i5)'),
        ('N', 'No Indexing')
    )

    index_format = models.CharField(
        'Index format',
        max_length=50,
        blank=False,
        null=False,
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
        'Index Sequence',
        max_length=50,
        blank=True,
        null=True,
    )

    sample = models.ForeignKey(
        Sample,
        on_delete=models.CASCADE,
    )

    class Meta:
        unique_together = ('dna_library', 'index_sequence')


class SequenceLane(models.Model):
    """
    Lane of Illumina Sequencing.
    """

    history = HistoricalRecords()

    flowcell_id = create_id_field('FlowCell ID')

    lane_number = models.PositiveSmallIntegerField(
        'Lane Number',
        blank=False,
        null=False,
    )

    sequencing_centre = create_id_field('Sequencing Centre')

    sequencing_library_id = create_id_field('Sequencing Library ID')

    sequencing_instrument_choices = (
        ('HX','HiSeqX'),
        ('H2500','HiSeq2500'),
        ('N550','NextSeq550'),
        ('MI','MiSeq'),
        ('O','other'),
    )

    sequencing_instrument = models.CharField(
        'Sequencing instrument',
        max_length=50,
        blank=False,
        null=False,
        choices=sequencing_instrument_choices,
    )

    read_type_choices = (
        ('P', 'PET'),
        ('S', 'SET')
    )

    read_type = models.CharField(
        'Read type',
        max_length=50,
        blank=False,
        null=False,
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


class SequenceDataset(PolymorphicModel):
    """
    General Sequence Dataset.
    """

    tags = TaggableManager()
    history = HistoricalRecords()

    lanes = models.ManyToManyField(
        SequenceLane,
        verbose_name='Lanes',
        blank=False,
    )
    
    dna_sequences = models.ForeignKey(
        DNASequences,
        on_delete=models.CASCADE,
    )

    sequence_data = models.ManyToManyField(
        SequenceDataFile,
        verbose_name='Data',
        blank=False,
    )


class SingleEndFastqFile(SequenceDataset):
    """
    Fastq file of single ended Illumina Sequencing.
    """

    history = HistoricalRecords()

    reads_file = models.ForeignKey(
        SequenceDataFile,
        on_delete=models.CASCADE,
        related_name='reads_file',
    )

    def __str__(self):
        return "SingleEndFastQ {}".format(self.id)

    filename_template = '{sample_id}/{library_type}/{sample_id}_{library_type}_{date}_{uid}.fastq{compression}'

    def default_reads_filename(self):
        return self.filename_template.format(
            sample_id=self.dna_sequences.sample.sample_id,
            library_type=self.dna_sequences.dna_library.library_type,
            date=self.reads_file.get_filename_time(),
            uid=self.reads_file.get_filename_uid(),
            compression=self.reads_file.get_compression_suffix())


class PairedEndFastqFiles(SequenceDataset):
    """
    Fastq file of paired ended Illumina Sequencing.
    """

    history = HistoricalRecords()

    reads_1_file = models.ForeignKey(
        SequenceDataFile,
        on_delete=models.CASCADE,
        related_name='reads_1_file',
    )

    reads_2_file = models.ForeignKey(
        SequenceDataFile,
        on_delete=models.CASCADE,
        related_name='reads_2_file',
    )

    def __str__(self):
        return "PairedEndFastq {}".format(self.id)

    filename_template = '{sample_id}/{library_type}/{sample_id}_{library_type}_{date}_{uid}_{read_end}.fastq{compression}'

    def default_reads_1_filename(self):
        return self.filename_template.format(
            sample_id=self.dna_sequences.sample.sample_id,
            library_type=self.dna_sequences.dna_library.library_type,
            date=self.reads_1_file.get_filename_time(),
            uid=self.reads_1_file.get_filename_uid(),
            read_end='1',
            compression=self.reads_1_file.get_compression_suffix())

    def default_reads_2_filename(self):
        return self.filename_template.format(
            sample_id=self.dna_sequences.sample.sample_id,
            library_type=self.dna_sequences.dna_library.library_type,
            date=self.reads_2_file.get_filename_time(),
            uid=self.reads_2_file.get_filename_uid(),
            read_end='2',
            compression=self.reads_2_file.get_compression_suffix())


class BamFile(SequenceDataset):
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
        'Reference Genome',
        max_length=50,
        blank=False,
        null=False,
        choices=reference_genome_choices,
    )

    aligner = models.CharField(
        'Aligner',
        max_length=50,
        blank=False,
        null=False,
    )

    bam_file = models.ForeignKey(
        SequenceDataFile,
        on_delete=models.CASCADE,
        related_name='bam_file',
    )

    bam_index_file = models.ForeignKey(
        SequenceDataFile,
        on_delete=models.CASCADE,
        related_name='bam_index_file',
    )

    filename_template = '{sample_id}/{library_type}/{sample_id}_{library_type}_{date}_{uid}.{suffix}'

    def default_bam_filename(self):
        return self.filename_template.format(
            sample_id=self.dna_sequences.sample.sample_id,
            library_type=self.dna_sequences.dna_library.library_type,
            date=self.reads_1_file.get_filename_time(),
            uid=self.reads_1_file.get_filename_uid(),
            suffix='bam')

    def default_bam_index_filename(self):
        return self.filename_template.format(
            sample_id=self.dna_sequences.sample.sample_id,
            library_type=self.dna_sequences.dna_library.library_type,
            date=self.reads_2_file.get_filename_time(),
            uid=self.reads_2_file.get_filename_uid(),
            suffix='bam.bai')


class Storage(PolymorphicModel):
    """
    Details of a specific file storage location.
    """

    history = HistoricalRecords()

    name = models.CharField(
        'Name',
        max_length=50,
        blank=False,
        null=False,
    )

    def __unicode__(self):
        return '{}'.format(self.name)


class ServerStorage(Storage):
    """
    Server file storage for sequence data files.
    """

    history = HistoricalRecords()

    server_ip = models.CharField(
        'Server IP',
        max_length=50,
        blank=False,
        null=False,
    )

    storage_directory = models.CharField(
        'Storage Directory',
        max_length=500,
        blank=False,
        null=False,
    )


class AzureBlobStorage(Storage):
    """
    Azure blob storage for sequence files.
    """

    history = HistoricalRecords()

    storage_account = models.CharField(
        'Storage Account',
        max_length=50,
        blank=False,
        null=False,
    )

    storage_container = models.CharField(
        'Storage Container',
        max_length=50,
        blank=False,
        null=False,
    )

    storage_key = models.CharField(
        'Storage Key',
        max_length=200,
        blank=False,
        null=False,
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
        SequenceDataFile,
        on_delete=models.CASCADE,
    )

    filename = models.CharField(
        'Filename',
        max_length=500,
        blank=False,
        null=False,
    )

    class Meta:
        unique_together = ('file_resource', 'storage')

class FileTransfer(models.Model):
    """
    Transfer of a specific data file.
    """

    file_instance = models.ForeignKey(
        FileInstance,
        blank=False,
        null=False,
    )

    new_filename = models.CharField(
        'New Filename',
        max_length=500,
        blank=False,
        null=False,
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
        blank=False,
        null=False,
        related_name='deployment_from_storage',
    )

    to_storage = models.ForeignKey(
        Storage,
        blank=False,
        null=False,
        related_name='deployment_to_storage',
    )

    datasets = models.ManyToManyField(
        SequenceDataset,
        verbose_name='Datasets',
        blank=False,
    )

    file_transfers = models.ManyToManyField(
        FileTransfer,
        verbose_name='File Transfers',
        blank=False,
    )

    running = models.BooleanField('Running', default=False)
    finished = models.BooleanField('Finished', default=False)
    errors = models.BooleanField('Errors', default=False)


