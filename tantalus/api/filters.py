"""Contains filters for API viewsets."""

from django.db import models
from django_filters import rest_framework as filters
from tantalus.models import (
    Analysis,
    DNALibrary,
    FileInstance,
    FileResource,
    FileType,
    Dataset,
    Sample,
    SequenceFileInfo,
    SequencingLane,
    ServerStorage,
    Storage,
    Tag,
)


class BaseFilterSet(filters.FilterSet):
    """Base filterset class.

    Specify some common attributes for all filters.
    """

    class Meta:
        """Override browsable filter boxes

        Remember to inherit the Meta class in children as in the
        following:

            >>> class Meta(BaseFilterSet.Meta):
            ...     # stuff here
        """

        # Make relational fields have a text input box in the browser,
        # else loading all related rows will take *ages*
        filter_overrides = {
            models.ForeignKey: {"filter_class": filters.CharFilter},
            models.ManyToManyField: {"filter_class": filters.CharFilter},
            models.OneToOneField: {"filter_class": filters.CharFilter},
        }


class AnalysisFilter(BaseFilterSet):
    """Filters for analyses."""

    class Meta(BaseFilterSet.Meta):
        model = Analysis
        fields = {
            "id": ["exact"],
            "name": ["exact"],
            "version": ["exact"],
            "jira_ticket": ["exact"],
            "analysis_type__name": ["exact"],
            "version": ["exact"],
            "input_datasets__id": ["exact"],
            "input_results__id": ["exact"],
        }


class DNALibraryFilter(BaseFilterSet):
    """Filters for DNA libraries."""

    class Meta(BaseFilterSet.Meta):
        model = DNALibrary
        fields = {"id": ["exact"], "library_id": ["exact"]}


class FileInstanceFilter(BaseFilterSet):
    """Filters for file instances."""

    class Meta(BaseFilterSet.Meta):
        model = FileInstance
        fields = {
            "id": ["exact"],
            "storage__name": ["exact"],
            "file_resource": ["exact"],
            "owner": ["exact"],
            "storage": ["exact"],
            "is_deleted": ["exact"],
        }


class FileResourceFilter(BaseFilterSet):
    """Filters for file resources."""

    def __init__(self, *args, **kwargs):
        """Take care of filter names that render poorly."""
        super(FileResourceFilter, self).__init__(*args, **kwargs)
        self.filters["dataset__id"].label = "Has Dataset ID"
        self.filters["dataset__name"].label = "Has Dataset name"
        self.filters["sequencefileinfo__index_sequence"].label = "Index Sequence"
        self.filters["fileinstance__storage__name"].label = "Is in Storage name"

    class Meta(BaseFilterSet.Meta):
        model = FileResource
        fields = {
            "id": ["exact"],
            "filename": ["exact", "endswith"],
            "dataset__name": ["exact"],
            "dataset__id": ["exact"],
            "sequencefileinfo__index_sequence": ["exact"],
            "fileinstance__storage__name": ["exact"],
        }


class FileTypeFilter(BaseFilterSet):
    """Filters for file types."""

    class Meta(BaseFilterSet.Meta):
        model = FileType
        fields = {
            "id": ["exact"],
            "name": ["exact"],
            "extension": ["exact"],
        }


class ResultsDatasetFilter(filters.FilterSet):
    """Filters for results datasets."""

    class Meta(BaseFilterSet.Meta):
        model = Dataset
        fields = {
            "id": ["exact"],
            "owner": ["exact"],
            "name": ["exact"],
            "analysis": ["exact"],
            "file_resources__filename": ["exact"],
            "results_type": ["exact"],
            "results_version": ["exact"],
            "tags__name": ["exact"],
            "libraries__library_id": ["exact"],
        }


class SampleFilter(BaseFilterSet):
    """Filters for samples."""

    def __init__(self, *args, **kwargs):
        """Take care of filter names that render poorly."""
        super(SampleFilter, self).__init__(*args, **kwargs)
        self.filters["dataset__id"].label = "Has Dataset"
        self.filters["dataset__id__in"].label = "Has Dataset in"
        self.filters["dataset__id__isnull"].label = "Has no eDatasets"

    class Meta(BaseFilterSet.Meta):
        model = Sample
        fields = {
            "id": ["exact", "in"],
            "sample_id": ["exact", "in"],
            "dataset__id": ["exact", "in", "isnull"],
        }


class SequenceDatasetFilter(filters.FilterSet):
    """Filters for sequence datasets."""

    class Meta(BaseFilterSet.Meta):
        model = Dataset
        fields = {
            "id": ["exact"],
            "name": ["exact"],
            "tags__name": ["exact"],
            "sequence_lanes__flowcell_id": ["exact"],
            "sequence_lanes__lane_number": ["exact"],
            "dataset_type": ["exact"],
            "aligner__name": ["exact"],
            "reference_genome__name": ["exact"],
            "analysis": ["exact"],
            "analysis__name": ["exact"],
            "analysis__jira_ticket": ["exact"],
            "file_resources__filename": ["exact"],
        }


class SequenceFileInfoFilter(BaseFilterSet):
    """Filters for sequence file infos."""

    class Meta(BaseFilterSet.Meta):
        model = SequenceFileInfo
        fields = {
            "id": ["exact"],
            "file_resource": ["exact"],
            "index_sequence": ["exact"],
        }


class SequencingLaneFilter(BaseFilterSet):
    """Filters for sequencing lanes."""

    class Meta(BaseFilterSet.Meta):
        model = SequencingLane
        fields = {
            "id": ["exact"],
            "dna_library__library_id": ["exact"],
            "flowcell_id": ["exact"],
            "lane_number": ["exact"],
            "sequencing_library_id": ["exact"],
            "read_type": ["exact"],
            "dna_library": ["exact"],
            "sequencing_centre": ["exact"],
        }


class ServerStorageFilter(BaseFilterSet):
    """Filters for server storages."""

    class Meta(BaseFilterSet.Meta):
        model = ServerStorage
        fields = {"id": ["exact"], "name": ["exact"]}


class StorageFilter(BaseFilterSet):
    """Filters for storages."""

    class Meta(BaseFilterSet.Meta):
        model = Storage
        fields = {"id": ["exact"], "name": ["exact"]}


class TagFilter(BaseFilterSet):
    """Filters for tags."""

    class Meta(BaseFilterSet.Meta):
        model = Tag
        fields = {"name": ["exact"]}
