from tantalus.models import *
from tantalus.utils import *

def get_curation_change(curation_name):
    '''
    Generating the edit history of the given curation.
    '''
    curation_history_lst = []
    #get the histories of the given curation
    curation_history = Curation.history.filter(name=curation_name).order_by('version')
    attributes = ["sequencedatasets", "owner", "description"]
    previous_curation = None
    #loop through the curation history
    for item in curation_history:
        current_curation = item.instance
        msg = "No field was modified."
        version = current_curation.version
        #check if this is the first history object of a curation
        if previous_curation:
            changes = []
            for attribute in attributes:
                if attribute == "sequencedatasets":
                    added_list = []
                    deleted_list = []
                    added = CurationDataset.history.filter(
                        curation_instance__name=current_curation.name,
                        version=version,
                        history_type='+')
                    deleted = CurationDataset.history.filter(
                        curation_instance__name=current_curation.name,
                        version=previous_curation.version,
                        history_type='-')
                    if added or deleted:
                        added_msg = ""
                        deleted_msg = ""
                        for added_dataset in added:
                            added_list.append(str(added_dataset.sequencedataset_instance.id))
                        for deleted_dataset in deleted:
                            deleted_list.append(str(deleted_dataset.sequencedataset_instance.id))
                        if added_list:
                            added_msg = ", ".join(added_list) + " added"
                        if deleted_list:
                            deleted_msg = ", ".join(deleted_list) + " deleted"
                        change = "SequenceDataset(s) %s %s" % (added_msg, deleted_msg)
                        changes.append(change)
                else:
                    if getattr(previous_curation, attribute) != getattr(current_curation, attribute):
                        change = "Field '%s' changed from %s to %s" % \
                            (attribute, getattr(previous_curation, attribute), getattr(current_curation, attribute))
                        changes.append(change)
            if changes:
                msg = "; ".join(changes)
            current_history = create_curation_modification_detail(msg, "Edited", current_curation)
        # if it is the first history object, then format the log message with "... is created with"
        else:
            changes = []
            for attribute in attributes:
                if attribute == "sequencedatasets":
                    datasets = CurationDataset.history.filter(
                        curation_instance__name=current_curation.name,
                        version=version,
                        history_type='+')
                    added_list = [str(ds.sequencedataset_instance.id) for ds in datasets]
                    added_msg = ", ".join(added_list)
                    change = "Field 'Sequence Dataset' is created with %s" % (added_msg)
                else:
                    change = "Field '%s' is created with %s" % (attribute, getattr(current_curation, attribute))
                changes.append(change)
            msg = "; ".join(changes) + "."
            current_history = create_curation_modification_detail(msg, "Created", current_curation)
        previous_curation = current_curation
        curation_history_lst.append(current_history)

    return curation_history_lst
