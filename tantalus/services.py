import tantalus.models
from tantalus.utils import *

def get_curation_change(old_instance, new_instance):
    '''
    Compare the old and new curation instance, then store the changes in the log message.
    '''
    attributes = ["sequencedatasets", "owner", "description"]
    new_data = new_instance.get_data()
    changes = []
    msg = "No field was modified."
    if old_instance:
        old_data = old_instance.get_data()

        for attribute in attributes:
            if attribute == "sequencedatasets":
                old = old_data[attribute]
                new = new_data[attribute]
                #find the added seq datasets
                added = list(set(new) - set(old))
                #find the deleted seq datasets
                deleted = list(set(old) - set(new))
                #generate the log message
                change = "SequenceDataset(s) %s added, %s deleted." % (added, deleted)
            else:
                if old_data[attribute] != new_data[attribute]:
                    change = "'%s' changed from %s to %s" % (attribute, old_data[attribute], new_data[attribute])
                    changes.append(change)

    else:
        for attribute in attributes:
            change = "'%s' is created with %s" % (attribute, new_data[attribute])
            changes.append(change)
    if changes:
        msg = "; ".join(changes) + "."
    return msg
