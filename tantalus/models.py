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


def create_id_field(name):
    return models.CharField(
        name,
        max_length=50,
        blank=False,
        null=False,
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

    sample_id = create_id_field('Sample ID')

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

    def __unicode__(self):
        return '{}'.format(self.md5)


class DNALibrary(models.Model):
    """
    DNA Library, possibly multiplexed.
    """

    history = HistoricalRecords()

    library_id = create_id_field('Library ID')

    library_type_choices = [
        ('Exome','Bulk Whole Exome Sequence'),
        ('WGS','Bulk Whole Genome Sequence'),
        ('SC WGS','Single Cell Whole Genome Sequence'),
        ('RNA-Seq','Bulk RNA-Seq'),
        ('SC RNA-Seq','Single Cell RNA-Seq'),
    ]

    library_type = models.CharField(
        'Library Type',
        max_length=50,
        blank=False,
        null=False,
        choices=library_type_choices,
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

    index_format_choices = [
        ('S', 'Single'),
        ('D', 'Dual'),
    ]

    index_format = models.CharField(
        'Index Format',
        max_length=50,
        blank=True,
        null=True,
        choices=index_format_choices,
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


class SequenceLane(models.Model):
    """
    Lane of Illumina Sequencing.
    """

    history = HistoricalRecords()

    sequencing_centre = create_id_field('Sequencing Centre')

    flowcell_id = create_id_field('FlowCell ID')

    lane_number = models.PositiveSmallIntegerField(
        'Lane Number',
        blank=False,
        null=False,
    )

    dna_library = models.ForeignKey(
        DNALibrary,
        on_delete=models.CASCADE,
    )

    def __unicode__(self):
        return '{}_{}_{}'.format(self.sequencing_centre, self.flowcell_id, self.lane_number)


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
    
    dna_sequences = models.ManyToManyField(
        DNASequences,
        verbose_name='Sequences',
        blank=False,
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

    files = models.ManyToManyField(
        SequenceDataset,
        verbose_name='Datasets',
        blank=False,
    )

    state = models.CharField(
        'State',
        max_length=50,
        null=True,
    )

    result = models.IntegerField(
        'Result',
        null=True,
    )


class FileTransfer(models.Model):
    """
    Transfer of a specific data file.
    """

    deployment = models.ForeignKey(
        Deployment,
        blank=False,
        null=False,
    )

    datafile = models.ForeignKey(
        SequenceDataFile,
        blank=False,
        null=False,
    )

    state = models.CharField(
        'State',
        max_length=50,
        null=True,
    )

    result = models.IntegerField(
        'Result',
        null=True,
    )


