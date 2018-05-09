import os

#===========================
# Django imports
#---------------------------
from django import forms

#===========================
# App imports
#---------------------------
from django.db import transaction
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404

from .models import Sample, AbstractDataSet, FileTransfer, FileResource, SequenceLane, DNALibrary, Tag, GscWgsBamQuery, GscDlpPairedFastqQuery, BRCFastqImport, ServerStorage, Storage
import tantalus.tasks


#===========================
# Sample forms
#---------------------------
class SampleForm(forms.ModelForm):
    class Meta:
        model = Sample
        fields = "__all__"


class MultipleSamplesForm(forms.Form):
    samples = forms.CharField(
        label="Sample(s)",
        required=False,
        help_text="A white space separated list of sample IDs. Eg. SA928",
        widget=forms.widgets.Textarea
    )

    def clean(self):
        samples = self.get_sample_ids()
        if len(samples) == 0:
            raise forms.ValidationError('no samples')

    def get_sample_ids(self):
        if 'samples' not in self.cleaned_data:
            return []
        return self.cleaned_data['samples'].split()


class DatasetSearchForm(forms.Form):
    tagged_with = forms.CharField(
        label="Tagged with",
        help_text="A comma separated list of tags",
        required=False,
    )
    exclude = forms.CharField(
        label="Exclude",
        help_text="A comma separated list of tags you want to exclude",
        required=False,
    )
    library = forms.CharField(
        label="Library",
        required=False,
        help_text="A white space separated list of library IDs. Eg. A90652A",
        widget=forms.widgets.Textarea
    )
    sample = forms.CharField(
        label="Sample(s)",
        required=False,
        help_text="A white space separated list of sample IDs. Eg. SA928",
        widget=forms.widgets.Textarea
    )

    dataset_type = forms.MultipleChoiceField(
        choices=tuple([(c.__name__, c.__name__) for c in AbstractDataSet.__subclasses__()]),
        label="Dataset type",
        required=False,
        help_text="Type of files to process",
        widget=forms.widgets.CheckboxSelectMultiple()
    )
    storages = forms.MultipleChoiceField(
        choices=tuple([(s.name, s.name) for s in Storage.objects.all()]),
        required=False,
        help_text="Only look for files that are present in the selected storage.",
        widget=forms.widgets.CheckboxSelectMultiple(),
    )
    flowcell_id_and_lane = forms.CharField(
        label="Flowcell ID + lane number",
        required=False,
        help_text="A white space separated list of flowcell IDs and lane number. Eg. H3LGYCCXY_4 - H3LGYCCXY is the lane, 4 is the lane number",
        widget = forms.widgets.Textarea
    )

    sequencing_center = forms.ChoiceField(
        choices=(('', '---'),) + SequenceLane.sequencing_centre_choices,
        label="Sequencing center",
        required=False,
        help_text="Sequencing center that the data was obtained from"
    )

    sequencing_instrument = forms.ChoiceField(
        choices=(('', '---'),) + tuple(map(lambda x: (x[0], x[0]), list(SequenceLane.objects.all().values_list('sequencing_instrument').distinct()))),
        label="Sequencing instrument",
        required=False,
    )

    sequencing_library_id = forms.CharField(
        label="Sequencing library ID",
        required=False,
        help_text="A white space separated list of external sequencing library ids. " + \
                  "Note that this is different from internal library IDs. " + \
                  "For example, these are external library IDs given to us by the GSC, eg. PX0395",
        widget=forms.widgets.Textarea
    )

    library_type = forms.ChoiceField(
        choices=(('', '---'),) + DNALibrary.library_type_choices,
        label="Library type",
        required=False,
    )

    index_format = forms.ChoiceField(
        choices=(('', '---'),) + DNALibrary.index_format_choices,
        label="Index format",
        required=False,
    )

    num_read_groups = forms.IntegerField(
        label="Number of read groups",
        required=False,
    )

    def clean_tagged_with(self):
        tags = self.cleaned_data['tagged_with']
        if tags:
            tags_list = [tag.strip() for tag in tags.split(",")]
            results = AbstractDataSet.objects.all()
            for tag in tags_list:
                if not results.filter(tags__name=tag).exists():
                    raise forms.ValidationError("Filter for the following tags together resulted in 0 results: {}".format(
                        ", ".join(tags_list)
                    ))
        return tags

    def clean_sample(self):
        sample = self.cleaned_data['sample']
        if sample:
            no_match_samples = []
            for samp in sample.split():
                if not AbstractDataSet.objects.filter(read_groups__sample__sample_id=samp).exists():
                    no_match_samples.append(samp)
            if no_match_samples != []:
                raise forms.ValidationError("Filter for the following sample resulted in 0 results: {}".format(
                    ", ".join(no_match_samples)
                ))
        return sample

    def clean_library(self):
        library = self.cleaned_data['library']
        if library:
            no_match_list = []
            for lib in library.split():
                if not AbstractDataSet.objects.filter(read_groups__dna_library__library_id=lib).exists():
                    no_match_list.append(lib)

            if no_match_list:
                raise forms.ValidationError("Filter for the following library resulted in 0 results: {}".format(
                    ", ".join(no_match_list)
                ))
        return library

    def clean_flowcell_id_and_lane(self):
        flowcell_and_lane_number_input = self.cleaned_data['flowcell_id_and_lane']
        if flowcell_and_lane_number_input:
            no_match_list = []
            for flowcell_lane in flowcell_and_lane_number_input.split():
                if "_" in flowcell_lane:
                    # parse out flowcell ID and lane number, assumed to be separated by an underscore
                    flowcell, lane_number = flowcell_lane.split("_", 1)
                    if not AbstractDataSet.objects.filter(
                            read_groups__sequence_lane__flowcell_id=flowcell, read_groups__sequence_lane__lane_number=lane_number).exists():
                        no_match_list.append(flowcell_lane)
                else:
                    # no lane number included
                    if not AbstractDataSet.objects.filter(read_groups__sequence_lane__flowcell_id=flowcell_lane).exists():
                        no_match_list.append(flowcell_lane)
            if no_match_list:
                raise forms.ValidationError("Filter for the following flowcell lane resulted in 0 results: {}".format(
                    ", ".join(no_match_list)
                ))
        return flowcell_and_lane_number_input

    def clean_sequencing_library_id(self):
        sequencing_library_id_field = self.cleaned_data['sequencing_library_id']
        if sequencing_library_id_field:
            no_match_list = []
            for sequencing_library in sequencing_library_id_field.split():
                if not AbstractDataSet.objects.filter(read_groups__sequence_lane__sequencing_library_id=sequencing_library).exists():
                    no_match_list.append(sequencing_library)
            if no_match_list:
                raise forms.ValidationError("Filter for the following sequencing library resulted in 0 results: {}".format(
                    no_match_list
                ))
        return sequencing_library_id_field

    def clean(self):
        cleaned_data = super(DatasetSearchForm, self).clean()
        results = self.get_dataset_search_results(clean=False, **cleaned_data)

        if len(results) == 0:
            raise forms.ValidationError(
                "Found zero datasets."
            )

    def get_dataset_search_results(self, clean=True, exclude=None, tagged_with=None, library=None, sample=None, dataset_type=None,storages=None,
                                   flowcell_id_and_lane=None, sequencing_center=None,
                                   sequencing_instrument=None, sequencing_library_id=None, library_type=None,
                                   index_format=None, num_read_groups=None):
        """
        Performs the filter search with the given fields. The "clean" flag is used to indicate whether the cleaned data
        should be used or not.
            - This method gets called in the cleaning method - where the data is not yet guaranteed to be clean,
            and also outside, where the data can be trusted to be clean

        :param tags: list of tag strings separated by commas
        :param library: Library id. Eg. A90652A
        :param sample: Sample id. Eg. SA928
        :param clean: Flag indicating whether or not the data has been cleaned yet
        :return:
        """

        if clean:
            tagged_with = self.cleaned_data['tagged_with']
            exclude = self.cleaned_data['exclude']
            library = self.cleaned_data['library']
            sample = self.cleaned_data['sample']
            dataset_type = self.cleaned_data['dataset_type']
            storages = self.cleaned_data['storages']
            flowcell_id_and_lane = self.cleaned_data['flowcell_id_and_lane']
            sequencing_center = self.cleaned_data['sequencing_center']
            sequencing_instrument = self.cleaned_data['sequencing_instrument']
            sequencing_library_id = self.cleaned_data['sequencing_library_id']
            library_type = self.cleaned_data['library_type']
            index_format = self.cleaned_data['index_format']
            num_read_groups = self.cleaned_data['num_read_groups']


        results = AbstractDataSet.objects.all()

        # TODO: add prefetch related

        if tagged_with:
            tags_list = [tag.strip() for tag in tagged_with.split(",")]
            exclude_list = [tag.strip() for tag in exclude.split(",")]
            for tag in tags_list:
                results = results.filter(tags__name=tag).exclude(tags__name__in=exclude_list)

        if sample:
            results = results.filter(read_groups__sample__sample_id__in=sample.split())

        if dataset_type:
            query = Q()
            for d_type in dataset_type:
                temp_query = {"{}__isnull".format(d_type.lower()): False}
                query = query | Q(**temp_query)
            results = results.filter(query)

        if storages:
            results = results.filter(file_resources__fileinstance__storage__name__in=storages)

        if library:
            results = results.filter(read_groups__dna_library__library_id__in=library.split())

        if sequencing_center:
            results = results.filter(read_groups__sequence_lane__sequencing_centre=sequencing_center)

        if sequencing_instrument:
            results = results.filter(read_groups__sequence_lane__sequencing_instrument=sequencing_instrument)

        if sequencing_library_id:
            results = results.filter(read_groups__sequence_lane__sequencing_library_id__in=sequencing_library_id.split())

        if library_type:
            results = results.filter(read_groups__dna_library__library_type=library_type)

        if index_format:
            results = results.filter(read_groups__dna_library__index_format=index_format)
 
        if num_read_groups is not None:
            results = results.annotate(num_read_groups=Count('read_groups')).filter(num_read_groups=num_read_groups)

        if flowcell_id_and_lane:
            query = Q()
            for flowcell_lane in flowcell_id_and_lane.split():
                if "_" in flowcell_lane:
                    # parse out flowcell ID and lane number, assumed to be separated by an underscore
                    flowcell, lane_number = flowcell_lane.split("_", 1)
                    q = Q(read_groups__sequence_lane__flowcell_id=flowcell, read_groups__sequence_lane__lane_number=lane_number)
                else:
                    q = Q(read_groups__sequence_lane__flowcell_id=flowcell_lane)
                query = query | q
            results = results.filter(query)

        results = results.distinct()

        return list(results.values_list('id', flat=True))


class DatasetTagForm(forms.Form):
    tag_name = forms.CharField(max_length=500)
    models_to_tag = None

    # use __init__ to populate models to tag field
    def __init__(self, *args, **kwargs):
        datasets = kwargs.pop('datasets', None)
        super(DatasetTagForm, self).__init__(*args, **kwargs)

        if datasets:
            self.models_to_tag = AbstractDataSet.objects.filter(pk__in=datasets)
        else:
            self.models_to_tag = AbstractDataSet.objects.all()

    def add_dataset_tags(self):
        tag_name = self.cleaned_data['tag_name']
        tag, created = Tag.objects.get_or_create(name=tag_name)
        tag.abstractdataset_set.clear()
        tag.abstractdataset_set.add(*self.models_to_tag)


class SimpleTaskCreateForm(forms.ModelForm):

    class Meta:
        abstract = True

    def save(self):
        super(SimpleTaskCreateForm, self).save()
        self.instance.state = self.instance.task_name.replace('_', ' ') + ' queued'
        self.task_type.apply_async(
            args=(self.instance.id,),
            queue=self.instance.get_queue_name())
        return self.instance


class FileTransferCreateForm(SimpleTaskCreateForm):

    task_name = 'transfer files'
    task_type = tantalus.tasks.transfer_files_task

    class Meta:
        model = FileTransfer
        fields = ('name', 'tag_name', 'from_storage', 'to_storage')

    def clean_tag_name(self):
        tag_name = self.cleaned_data['tag_name'].strip()
        datasets = AbstractDataSet.objects.filter(tags__name=tag_name)
        if len(datasets) == 0:
            raise forms.ValidationError('no datasets with tag {}'.format(tag_name))
        return tag_name


class GscWgsBamQueryCreateForm(SimpleTaskCreateForm):
    
    task_name = 'query GSC for WGS BAMs'
    task_type = tantalus.tasks.query_gsc_wgs_bams_task

    library_ids = forms.CharField(
        label="Library ids",
        required=False,
        help_text="A white space separated list of library IDs. Eg. A90652A",
        widget=forms.widgets.Textarea
    )

    def clean_library_ids(self):
        return self.cleaned_data['library_ids'].split()

    class Meta:
        model = GscWgsBamQuery
        fields = ('library_ids',)


class GscDlpPairedFastqQueryCreateForm(SimpleTaskCreateForm):

    task_name = 'query GSC for DLP fastqs'
    task_type = tantalus.tasks.query_gsc_dlp_paired_fastqs_task

    class Meta:
        model = GscDlpPairedFastqQuery
        fields = ('dlp_library_id', 'gsc_library_id')


class BRCFastqImportCreateForm(SimpleTaskCreateForm):

    task_name = 'import brc fastqs into tantalus'
    task_type = tantalus.tasks.import_brc_fastqs_task

    class Meta:
        model = BRCFastqImport
        fields = ('output_dir', 'storage', 'flowcell_id')
