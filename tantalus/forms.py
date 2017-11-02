import os

#===========================
# Django imports
#---------------------------
from django import forms

#===========================
# App imports
#---------------------------
from .models import Sample, AbstractDataSet

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
    library = forms.CharField(
        label="Library",
        required=False,
        help_text="Library id. Eg. A90652A"
    )
    sample = forms.CharField(
        label="Sample(s)",
        required=False,
        help_text="A white space separated list of sample IDs. Eg. SA928",
        widget=forms.widgets.Textarea
    )

    def clean_tagged_with(self):
        tags = self.cleaned_data['tagged_with']
        if tags:
            tags_list = [tag.strip() for tag in tags.split(",")]
            results = AbstractDataSet.objects.all()
            for tag in tags_list:
                results = results.filter(tags__name=tag)
                if results.count() == 0:
                    raise forms.ValidationError("Filter for the following tags together resulted in 0 results: {}".format(
                        ", ".join(tags_list)
                    ))
        return tags

    def clean_sample(self):
        sample = self.cleaned_data['sample']
        if sample:
            sample_list = sample.split()
            no_match_samples = []
            for samp in sample_list:
                results = AbstractDataSet.objects.filter(dna_sequences__sample__sample_id__iexact=samp)
                if results.count() == 0:
                    no_match_samples.append(samp)
            if no_match_samples != []:
                raise forms.ValidationError("Filter for the following sample resulted in 0 results: {}".format(
                    ", ".join(no_match_samples)
                ))
        return sample

    def clean_library(self):
        library = self.cleaned_data['library']
        if library != "":
            results = AbstractDataSet.objects.filter(dna_sequences__dna_library__library_id__iexact=library)
            if results.count() == 0:
                raise forms.ValidationError("Filter for the following library resulted in 0 results: {}".format(
                    library
                ))
        return library

    def clean(self):
        cleaned_data = super(DatasetSearchForm, self).clean()
        tags = cleaned_data.get('tags_list')
        library = cleaned_data.get('library')
        sample = cleaned_data.get('sample')

        results = self.get_dataset_search_results(tags=tags, library=library, sample=sample, clean=False)

        if len(results) == 0:
            raise forms.ValidationError(
                "Found zero datasets."
            )


    def get_dataset_search_results(self, tags=None, library=None, sample=None, clean=True):
        """
        Performs the filter search with the given fields. The "clean" flag is used to indicate whether the cleaned data
        should be used or not

        :param tags: list of tag strings separated by commas
        :param library: Library id. Eg. A90652A
        :param sample: Sample id. Eg. SA928
        :param clean: Flag indicating whether or not the data has been cleaned yet
        :return:
        """

        if clean:
            tags = self.cleaned_data['tagged_with']
            library = self.cleaned_data['library']
            sample = self.cleaned_data['sample']

        results = AbstractDataSet.objects.all()

        if tags:
            tags_list = [tag.strip() for tag in tags.split(",")]
            for tag in tags_list:
                results = results.filter(tags__name=tag)

        if sample:
            sample_list = sample.split()
            results = AbstractDataSet.objects.filter(dna_sequences__sample__sample_id__in=sample_list)

        if library != "":
            results = results.filter(dna_sequences__dna_library__library_id__iexact=library)

        return list(results.values_list('id', flat=True))



class DatasetTagForm(forms.Form):
    tag_name = forms.CharField(max_length=500)
    models_to_tag = forms.ModelMultipleChoiceField(
        label="Datasets to tag",
        queryset=None,
        help_text="All datasets returned by search will be tagged by default. Use the search in the dropdown and unselect those you want to exclude."
    )

    # use __init__ to populate models to tag field
    def __init__(self, *args, **kwargs):
        datasets = kwargs.pop('datasets', None)
        super(DatasetTagForm, self).__init__(*args, **kwargs)

        if datasets:
            self.fields['models_to_tag'].queryset = AbstractDataSet.objects.filter(pk__in=datasets)
        else:
            self.fields['models_to_tag'].queryset = AbstractDataSet.objects.all()

    def add_dataset_tags(self):
        models_to_tag = self.cleaned_data['models_to_tag']
        tag_name = self.cleaned_data['tag_name']

        for dataset in models_to_tag:
            dataset.tags.add(tag_name)






