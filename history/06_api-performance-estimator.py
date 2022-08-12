from constants import *
import numpy as np
import pickle


########################################################################################################################
EXPERIMENT_ID = '202207302259_202207310221'
API_OF_INTEREST = '/wrk2-api/post/compose'
RTT_MICROSECONDS = 38500
SPEED_MICROSECONDS_PER_BYTE = 1 / 1.25
MIGRATION_PLAN = {'user-service', 'media-service', 'text-service', 'social-graph-service'}
########################################################################################################################

print('=====%s' % ('=' * len(API_OF_INTEREST)))
print('API: %s' % API_OF_INTEREST)
print('=====%s' % ('=' * len(API_OF_INTEREST)))
print('Migrated Components: %s' % ', '.join(list(MIGRATION_PLAN)))
print('')


# api_of_interest = '/wrk2-api/user/login'
# api_of_interest = '/wrk2-api/user/register'
# api_of_interest = '/wrk2-api/user/follow'
# api_of_interest = '/wrk2-api/user/unfollow'
# api_of_interest = '/upload-media'
# api_of_interest = '/get-media'
# api_of_interest = '/wrk2-api/home-timeline/read'
# api_of_interest = '/wrk2-api/user-timeline/read'
# api_of_interest = '/wrk2-api/post/compose'

with open('./experiments/%s/04_network-footprint-learning.pkl' % EXPERIMENT_ID, 'rb') as f:
    data_footprint = pickle.load(f)
with open('./experiments/%s/05_representative-traces.pkl' % EXPERIMENT_ID, 'rb') as f:
    repr_traces = pickle.load(f)


def get_duration(span, traceMap):
    return int(sum((log if type(log) != list else max(_offset + get_duration(traceMap[_spanID], traceMap) for _offset, _spanID in log)) for log in span['logs']))


def estimate_single(trace):
    api = API_OF_INTEREST

    # Add children to parent nodes for forward access
    spanID2dict = {}
    for span in trace:
        spanID = span['spanID']
        spanID2dict[spanID] = span
        span['children'] = []
        if len(span['references']) > 0:
            parent_spanID = span['references'][0]['spanID']
            for _span in trace:
                if parent_spanID == _span['spanID']:
                    _span['children'].append(spanID)
    # TODO: Check whether the entire subtree is a background job
    # for span in trace:
    #     if span['operationName'] != 'InsertUniqueIdToPost':
    #         continue
    #     maxDuration = span['duration']
    #     for spanID in span['children']:
    #         if spanID2dict[spanID]['operationName'] in ['StorePost', 'WriteUserTimeline']:
    #             maxDuration = max(maxDuration, spanID2dict[spanID]['startTime'] + spanID2dict[spanID]['duration'] - span['startTime'])
    #     span['duration'] = maxDuration

    _trace = []
    _traceMap = {}
    for span in trace:
        spanID = span['spanID']
        spanStartTime = span['startTime']
        spanEndTime = span['startTime'] + span['duration']
        operationName = span['operationName'].replace('/wrk2-api/user', '')
        serviceName = list(filter(lambda x: x['key'] == 'container.name', span['process']['tags']))[0]['value']
        if (serviceName, operationName) in SPAN_MAPPING:
            (serviceName, operationName) = SPAN_MAPPING[(serviceName, operationName)]
        children = span['children']

        clusters = []
        for child in children:
            child_startTime = spanID2dict[child]['startTime']
            child_endTime = child_startTime + spanID2dict[child]['duration']
            child_isForeground = spanEndTime >= spanID2dict[child]['startTime'] + spanID2dict[child]['duration']
            if not child_isForeground:
                # If the span was a background job, there is no need to include it in the tree because it does not
                # affect the API performance.
                continue

            child_range = set(list(range(child_startTime, child_endTime)))

            max_overlapping, max_cid = 0.10, -1
            for cid, cluster in enumerate(clusters):
                cluster_startTime = spanID2dict[cluster[0][1]]['startTime']
                cluster_endTime = max(
                    spanID2dict[_spanID]['startTime'] + spanID2dict[_spanID]['duration'] for _offset, _spanID in
                    cluster)
                cluster_range = set(list(range(cluster_startTime, cluster_endTime)))
                overlapping = len(cluster_range.intersection(child_range)) / len(child_range)
                if overlapping >= max_overlapping:
                    max_overlapping = overlapping
                    max_cid = cid
            if max_cid >= 0:  # parallel execution
                cluster_startTime = spanID2dict[clusters[max_cid][0][1]]['startTime']
                clusters[max_cid].append((child_startTime - cluster_startTime, child))
            else:  # sequential execution
                clusters.append([(0, child)])

        logs = []
        time_ptr = span['startTime']
        for cluster in clusters:
            cluster_startTime = spanID2dict[cluster[0][1]]['startTime']
            logs.append(cluster_startTime - time_ptr)
            logs.append(cluster)
            time_ptr = cluster_startTime + max(
                _offset + spanID2dict[_spanID]['duration'] for _offset, _spanID in cluster)
        if len(children) > 0:
            logs.append(span['startTime'] + span['duration'] - time_ptr)
        else:
            logs.append(span['duration'])

        _span = {'spanID': spanID, 'operationName': operationName, 'serviceName': serviceName, 'logs': logs}
        _trace.append(_span)
        _traceMap[spanID] = _span

    groundtruth = trace[0]['duration']
    estimation = get_duration(_trace[0], _traceMap)
    assert groundtruth == estimation, 'Ground truth does no match estimation before migration!'

    for parentSpan in _trace:
        parentService = parentSpan['serviceName']
        for i, log in enumerate(parentSpan['logs']):
            if type(log) == list:
                is_intercloud = False
                childService = None
                for _, childSpan in log:
                    childService = _traceMap[childSpan]['serviceName']
                    if (parentService in MIGRATION_PLAN) != (childService in MIGRATION_PLAN):
                        is_intercloud = True
                        break
                if is_intercloud:
                    request_bytes = data_footprint[api][(parentService, childService)]['request']
                    response_bytes = data_footprint[api][(parentService, childService)]['response']
                    parentSpan['logs'][i - 1] += (RTT_MICROSECONDS + request_bytes * SPEED_MICROSECONDS_PER_BYTE)
                    parentSpan['logs'][i + 1] += (response_bytes * SPEED_MICROSECONDS_PER_BYTE)
    old_performance = groundtruth * 1e-3
    new_performance = get_duration(_trace[0], _traceMap) * 1e-3
    return old_performance, new_performance


if __name__ == '__main__':
    before, after = [], []
    for trace in repr_traces[API_OF_INTEREST]:
        trace = trace[1:] if 'media' in API_OF_INTEREST else trace[2:]
        old_performance, new_performance = estimate_single(trace)
        before.append(old_performance)
        after.append(new_performance)
    print('Before: %.4f' % np.mean(before))
    print('After : %.4f' % np.mean(after))
