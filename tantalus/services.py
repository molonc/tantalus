import tantalus.models
from tantalus.utils import *

def get_form_changes(curation_instance, changed_fields, request, form_data, original_data, user_operation):
    '''
    Helper function that fetches that changes happened in a form.
    '''
    #get the curation name
    curation_name = form_data["name"]
    #get the name of the user who is modifying the curation
    user = request.user
    #create an empty list to store the operations performed
    operations = []
    #if the curation is being modified by the user
    if original_data:
        for field in changed_fields:
            old = original_data[field]
            if field == "sequencedatasets":
                #get the current list of sequence datasets
                new = [seq_dataset.pk for seq_dataset in form_data[field]]
                #find the newly added seq datasets
                added = list(set(new) - set(old))
                #find the deleted seq datasets
                deleted = list(set(old) - set(new))
                operation = "SequenceDataset(s) %s added, %s deleted." % (added, deleted)
            else:
                new = form_data[field]
                operation = "%s changed from %s to %s" % (field, old, new)
            operations.append(operation)
            full_operation = ";\n".join(operations)
    #else, if the curation is being created
    else:
        for field in changed_fields:
            if field == "sequencedatasets":
                #get the current list of sequence datasets
                new = [seq_dataset.pk for seq_dataset in form_data[field]]
            else:
                new = form_data[field]
            operation = "%s: %s" % (field, new)
            operations.append(operation)
            full_operation = "Curation is created with the following values: " + "; ".join(operations)
    #join the list of operations

    #record this operation in the curation history table if exists
    history_set = tantalus.models.CurationHistory.objects.filter(curation=curation_instance)
    if history_set:
        #if there's modification history, then increase the version number
        latest_version = history_set.latest("version").version
        new_version = "v%s.0.0" % (int(latest_version.split(".")[0][1:]) + 1)
    else:
        #else, create a history object with version v1.0.0
        new_version = "v1.0.0"
    #create a history record
    history_object = create_curation_history(curation_instance, user, user_operation, full_operation, new_version)
    history_object.save()
