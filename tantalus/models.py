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


class SequenceFileResource(models.Model):
    """
    Base class of file sequence file resources.
    """

    history = HistoricalRecords()

    md5 = models.CharField(
        'MD5',
        max_length=50,
        blank=False,
        null=False,
    )

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

    sequencing_id = create_id_field('Sequencing ID')

    def __unicode__(self):
        return '{}_{}'.format(self.sample_id, self.sequencing_id)


class IndexedReads(models.Model):
    """
    Multiplexed read index information
    """

    history = HistoricalRecords()

    index_1 = models.CharField(
        'Index 1',
        max_length=50,
        blank=False,
        null=False,
    )

    index_2 = models.CharField(
        'Index 2',
        max_length=50,
        blank=False,
        null=False,
    )

    def __unicode__(self):
        return '{}-{}'.format(self.index_1, self.index_2)


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

    indices = models.ManyToManyField(
        IndexedReads,
        verbose_name="Indices",
    )

    def __unicode__(self):
        return '{}_{}_{}'.format(self.sequencing_centre, self.flowcell_id, self.lane_number)


class DNALibraryReadSet(models.Model):
    """
    Subset of a DNA Library, possibly multiplexed.
    """

    history = HistoricalRecords()

    dna_library = models.ForeignKey(
        DNALibrary,
        on_delete=models.CASCADE,
    )

    indices = models.ManyToManyField(
        IndexedReads,
        verbose_name="Indices",
    )

    def __unicode__(self):
        return '{}_{}_{}'.format(self.sequencing_centre, self.flowcell_id, self.lane_number)


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
        verbose_name="Lanes",
        blank=False,
    )
    
    read_set = models.ForeignKey(
        DNALibraryReadSet,
        on_delete=models.CASCADE,
    )

    reads_1_file = models.ForeignKey(
        SequenceFileResource,
        on_delete=models.CASCADE,
        related_name='asdf2',
    )

    reads_2_file = models.ForeignKey(
        SequenceFileResource,
        on_delete=models.CASCADE,
        related_name='asdf1',
    )

    def __unicode__(self):
        return 'fastq:{}'.format(SequenceFileResource.__unicode__(self))


class BamFile(SequenceFileResource):
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
        verbose_name="Lanes",
        blank=False,
    )

    read_set = models.ForeignKey(
        DNALibraryReadSet,
        on_delete=models.CASCADE,
    )

    bam_file = models.ForeignKey(
        SequenceFileResource,
        on_delete=models.CASCADE,
        related_name='abam_file',
    )

    bam_index_file = models.ForeignKey(
        SequenceFileResource,
        on_delete=models.CASCADE,
        related_name='abam_index_file',
    )

    def __unicode__(self):
        return 'bam:{}'.format(SequenceFileResource.__unicode__(self))


class ServerStorage(models.Model):
    """
    Server / Path location in which files are stored.
    """

    history = HistoricalRecords()

    name = models.CharField(
        'Store Name',
        max_length=50,
        blank=False,
        null=False,
    )

    server_name = models.CharField(
        'Server Name',
        max_length=50,
        blank=False,
        null=False,
    )

    directory = models.CharField(
        'Store Directory',
        max_length=250,
        blank=False,
        null=False,
    )

    def __unicode__(self):
        return '{}:{}'.format(self.server_name, self.directory)


class AzureBlobStorage(models.Model):
    """
    Azure blob storage for sequence files.
    """

    history = HistoricalRecords()

    name = models.CharField(
        'Store Name',
        max_length=50,
        blank=False,
        null=False,
    )

    account = models.CharField(
        'Storage Account',
        max_length=50,
        blank=False,
        null=False,
    )

    container = models.CharField(
        'Storage Container',
        max_length=50,
        blank=False,
        null=False,
    )

    def __unicode__(self):
        return '{}/{}'.format(self.account, self.container)


class ServerFileInstance(models.Model):
    """
    Instance of a sequence file.
    """

    history = HistoricalRecords()

    server_storage = models.ForeignKey(
        ServerStorage,
        on_delete=models.CASCADE,
    )

    filename = models.CharField(
        'Bam Filename',
        max_length=500,
        blank=False,
        null=False,
    )


class ServerBamFileInstance(ServerFileInstance):
    """
    Instance of a sequence file.
    """

    history = HistoricalRecords()

    bam_file = models.ForeignKey(
        BamFile,
        on_delete=models.CASCADE,
    )


class ServerPairedFastqFilesInstance(ServerFileInstance):
    """
    Instance of a sequence file.
    """

    history = HistoricalRecords()

    fastq_file = models.ForeignKey(
        PairedFastqFiles,
        on_delete=models.CASCADE,
    )

