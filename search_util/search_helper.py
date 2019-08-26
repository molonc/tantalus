import re
from django.contrib.postgres.search import SearchVector
from django.db.models import Q

from search_util.search_fields import *
from tantalus.models import *

def return_text_search(query):
    context = {
        "sample": {
            "Patients": [],
            "Samples" : [],
        },
        "analysis": {
            "Submissions" : [],
            "Analyses": [],
            "Tags" : []
        },
        "dataset": {
            "Datasets": [],
            "ResultDatasets": [],
        },
        "query" : query,
        "total" : 0
    }

    context["sample"]["Patients"].extend(list(Patient.objects.annotate(search=SearchVector(*PATIENT)).filter(Q(search=query) | Q(search__icontains=query))))
    context["sample"]["Samples"].extend(list(Sample.objects.annotate(search=SearchVector(*SAMPLE)).filter(Q(search=query) | Q(search__icontains=query))))
    context["dataset"]["Datasets"].extend(list(SequenceDataset.objects.annotate(search=SearchVector(*(SEQUENCE_DATASET))).filter(Q(search=query) | Q(search__icontains=query))))

    context["analysis"]["Submissions"].extend(list(Submission.objects.annotate(search=SearchVector(*(SUBMISSION))).filter(Q(search=query) | Q(search__icontains=query))))
    context["dataset"]["ResultDatasets"].extend(list(ResultsDataset.objects.annotate(search=SearchVector(*RESULT_DATASET)).filter(Q(search=query) | Q(search__icontains=query))))
    context["analysis"]["Analyses"].extend(list(Analysis.objects.annotate(search=SearchVector(*(ANALYSIS))).filter(Q(search=query) | Q(search__icontains=query))))
    context["analysis"]["Tags"].extend(list(Tag.objects.annotate(search=SearchVector(*(TAG))).filter(Q(search=query) | Q(search__icontains=query))))

    dict_sequencing_centre = dict((y, x) for x, y in SEQUENCING_CENTRE)
    dict_dataset_type = dict((y, x) for x, y in DATASET_TYPE)

    if partial_key_match(query, dict_sequencing_centre):
        context["dataset"]["Datasets"].extend(list(SequenceDataset.objects.filter(sequence_lane__sequencing_centre=partial_key_match(query, dict_sequencing_centre))))
    if partial_key_match(query, dict_dataset_type):
        context["dataset"]["Datasets"].extend(list(SequenceDataset.objects.filter(dataset_type=partial_key_match(query, dict_dataset_type))))

    context = remove_duplicate(context)

    context["total"] = len(context["sample"]["Patients"] + context["sample"]["Samples"] + context["dataset"]["Datasets"]+ context["analysis"]["Submissions"] +
                           context["dataset"]["ResultDatasets"] +  context["analysis"]["Analyses"] +  context["analysis"]["Tags"] )

    return context

def partial_key_match(lookup, dict):
    for key,value in dict.items():
        if lookup in key:
            return value
    return False


def remove_duplicate(context):
    context["sample"]["Patients"] = list(set(context["sample"]["Patients"]))
    context["sample"]["Samples"]  = list(set(context["sample"]["Samples"]))
    context["dataset"]["Datasets"] = list(set(context["dataset"]["Datasets"]))
    context["analysis"]["Submissions"] = list(set(context["analysis"]["Submissions"]))
    context["dataset"]["ResultDatasets"] = list(set(context["dataset"]["ResultDatasets"]))
    context["analysis"]["Analyses"] = list(set(context["analysis"]["Analyses"]))
    context["analysis"]["Tags"] = list(set(context["analysis"]["Tags"]))

    return context

