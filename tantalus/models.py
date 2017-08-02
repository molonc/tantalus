"""
Tantalus models
"""

from __future__ import unicode_literals

from django.db import models
import taggit.models
import simple_history
from simple_history.models import HistoricalRecords

# import taggit.managers
# from taggit.managers import TaggableManager
# from taggit.models import Tag
# from simple_history.models import HistoricalRecords
# from simple_history import register
# 

# register taggit for tracking its history
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

    created = models.DateField(
        'Created',
        null=False,
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


class PairedFastqFiles(models.Model):
    """
    Fastq file of Illumina Sequencing.
    """

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


class BamFile(models.Model):
    """
    Base class of bam files.
    """

    history = HistoricalRecords()

    reference_genome_choices = (
        ('hg19','Human Genome 19'),
        ('hg18','Human Genome 18'),
        ('none','No Useful alignments'),
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


class Server(models.Model):
    """
    Details of a specific file storage server.
    """

    history = HistoricalRecords()

    server_name = models.CharField(
        'Server Name',
        max_length=50,
        blank=False,
        null=False,
    )


class ServerFileInstance(models.Model):
    """
    Instance of a file on a server
    """

    history = HistoricalRecords()

    server = models.ForeignKey(
        Server,
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


class AzureBlobFileInstance(models.Model):
    """
    Azure blob storage for sequence files.
    """

    history = HistoricalRecords()

    file_resource = models.ForeignKey(
        SequenceDataFile,
        on_delete=models.CASCADE,
    )

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

    filename = models.CharField(
        'Filename',
        max_length=500,
        blank=False,
        null=False,
    )


class Transfer(models.Model):
    name = models.CharField(
        'Name',
        max_length=50,
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

