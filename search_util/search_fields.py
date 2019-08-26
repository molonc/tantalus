
#reverse map
# MAPPING = {
#     "Patient" : "P", "Cell Line" : "C", "Xenograft" : "X", "Other" : "O",
#     "Primary" : "PR", "Recurrent or Relapse" : "RC", "Metastatic" : "ME", "Remission": "RM",
# }

SEQUENCING_CENTRE = (
    ('GSC', 'Genome Science Centre'),
    ('BRC', 'Biomedical Research Centre'),
)

DATASET_TYPE = (
    ('BAM', 'BAM Files'),
    ('FQ', 'FastQ Files'),
    ('BCL', 'BCL Files'),
)

#fields to filter
SEQUENCE_DATASET = [ 'sample__sample_id', 'sample__external_sample_id', 'sample__tissue', 'sample__note',
                     'library__library_id', 'library__library_type', 'sequence_lanes__flowcell_id', 'sequence_lanes__sequencing_centre', 'sequence_lanes__sequencing_instrument',
                     'aligner__name', 'reference_genome__name', 'name', 'dataset_type', 'owner__username']

PATIENT = [ 'patient_id', 'reference_id', 'external_patient_id', 'patient_id', 'sample__sample_id']

SAMPLE = [ 'sample_id', 'projects__name', 'external_sample_id', 'submitter', 'researcher', 'tissue', 'note', 'patient__patient_id']

SUBMISSION = [ 'sample__sample_id', 'sow__name', 'submitted_by', 'library_type__name']

RESULT_DATASET = [ 'name', 'results_type', 'results_version', 'owner__username', 'tags__name',
                   'analysis__name', 'analysis__jira_ticket', 'analysis__status',
                   'samples__sample_id', 'samples__external_sample_id', 'samples__tissue', 'samples__note',
                   'libraries__library_type', 'libraries__library_id',
                   'inputresults__name'
                   ]

ANALYSIS = [ 'analysis_type', 'owner__username', 'name', 'jira_ticket', 'version', 'status', 'input_datasets__name', 'input_results__name' ]

TAG = [ 'name', 'owner__username', 'sequencedataset__name', 'resultsdataset__name']
