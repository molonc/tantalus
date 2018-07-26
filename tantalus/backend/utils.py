import hashlib


def get_lane_str(lane):
    if lane['lane_number'] == '':
        return '{}'.format(lane['flowcell_id'])
    else:
        return '{}_{}'.format(lane['flowcell_id'], lane['lane_number'])


def get_lanes_str(lanes):
    lanes = ', '.join(sorted([get_lane_str(a) for a in lanes]))
    lanes = hashlib.md5(lanes)
    return 'lanes {}'.format(lanes.hexdigest()[:8])


