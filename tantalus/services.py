import tantalus.models
###TODO: separate the case where a new curation is added and an existing curation if being changed
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
    #loop over the fields that have been changed by the user
    for field in changed_fields:
        if original_data:
            old = original_data[field]
        else:
            old = "None"
        if field == "sequencedatasets":
            #get the current list of sequence datasets
            new = [seq_dataset.pk for seq_dataset in form_data[field]]
            #find the newly added seq datasets
            added = list(set(new) - set(old))
            #find the deleted seq datasets
            deleted = list(set(old) - set(new))
            #record the operation
            print(old)
            operation = "SequenceDataset(s) %s added, %s deleted." % (added, deleted)
        else:
            new = form_data[field]
            operation = "%s changed from %s to %s" % (field, old, new)
        operations.append(operation)
    #join the list of operations
    full_operation = "; ".join(operations)
    #record this operation in the curation history table if exists
    history_set = tantalus.models.CurationHistory.objects.filter(curation=curation_instance)
    if history_set:
        latest_version = history_set.latest("version").version
        new_version = "v%s.0.0" % (int(latest_version.split(".")[0][1:])+1)
    else:
        new_version = "v1.0.0"
    print(new_version)
    history_object = tantalus.models.CurationHistory(
            curation=curation_instance,
            user_name=user,
            operation=user_operation,
            operation_description=full_operation,
            version=new_version
            )
    history_object.save()
