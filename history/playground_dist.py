from matplotlib import pyplot as plt
import numpy as np
import pickle


# api_of_interest = '/wrk2-api/user/login'
# api_of_interest = '/wrk2-api/user/register'
# api_of_interest = '/wrk2-api/user/follow'
# api_of_interest = '/wrk2-api/user/unfollow'
# api_of_interest = '/upload-media'
# api_of_interest = '/get-media'
api_of_interest = '/wrk2-api/home-timeline/read'
# api_of_interest = '/wrk2-api/user-timeline/read'
# api_of_interest = '/wrk2-api/post/compose'

rtt = 38500  # microseconds
microseconds_per_byte = 1 / 1.25  # 10 megabits/sec = 1.25 megabytes/sec
cloud_components = {'home-timeline-service'}

with open('./experiments/202207221540_202207221911/traces/200_202207221901.pkl', 'rb') as f:
# with open('./experiments/202207221540_202207221911/traces/11_202207221551.pkl', 'rb') as f:
    traces = list(filter(lambda trace: api_of_interest in trace[0]['operationName'], pickle.load(f).values()))

with open('./experiments/202207221540_202207221911/edge_bytes.pkl', 'rb') as f:
    data_footprint = pickle.load(f)

print('=====%s' % ('=' * len(api_of_interest)))
print('API: %s' % api_of_interest)
print('=====%s' % ('=' * len(api_of_interest)))
print('Migrated Components: %s' % ', '.join(list(cloud_components)))
print('')
mappings = {
    # /wrk2-api/post/compose
    ('url-shorten-service', 'MongoInsertUrls'): ('url-shorten-mongodb', 'InsertUrls'),
    ('user-mention-service', 'MmcGetUsers'): ('user-memcached', 'GetUsers'),
    ('user-mention-service', 'MongoFindUsers'): ('user-mongodb', 'FindUsers'),
    ('post-storage-service', 'MongoInsertPost'): ('post-storage-mongodb', 'InsertPost'),
    ('user-timeline-service', 'MongoInsertPost'): ('user-timeline-mongodb', 'InsertPost'),
    ('social-graph-service', 'RedisGet'): ('social-graph-redis', 'Get'),
    ('user-timeline-service', 'RedisUpdate'): ('user-timeline-redis', 'Update'),
    ('social-graph-service', 'MongoFindUser'): ('social-graph-mongodb', 'FindUser'),
    ('social-graph-service', 'RedisInsert'): ('social-graph-redis', 'Insert'),
    ('write-home-timeline-service', 'RedisUpdate'): ('home-timeline-redis', 'Update'),
    # /upload-media
    ('media-frontend', 'MongoInsertMedia'): ('media-mongodb', 'InsertMedia'),
    # /wrk2-api/home-timeline/read
    ('home-timeline-service', 'RedisFind'): ('home-timeline-redis', 'Find'),
    ('post-storage-service', 'MmcGetPosts'): ('post-storage-memcached', 'GetPosts'),
    ('post-storage-service', 'MongoFindPosts'): ('post-storage-mongodb', 'FindPosts'),
    ('post-storage-service', 'MmcSetPosts'): ('post-storage-memcached', 'SetPosts'),
    # /wrk2-api/user/login
    ('user-service', 'MmcGetLogin'): ('user-memcached', 'GetLogin'),
    ('user-service', 'MongoFindUser'): ('user-mongodb', 'FindUser'),
    ('user-service', 'MmcSetLogin'): ('user-memcached', 'SetLogin'),
    # /wrk2-api/user-timeline/read
    ('user-timeline-service', 'RedisFind'): ('user-timeline-redis', 'Find'),
    ('user-timeline-service', 'MongoFindUserTimeline'): ('user-timeline-mongodb', 'FindUserTimeline'),
    ('user-timeline-service', 'RedisUpdate'): ('user-timeline-redis', 'Update'),
    ('post-storage-service', 'MmcGetPosts'): ('post-storage-memcached', 'GetPosts'),
    ('post-storage-service', 'MongoFindPosts'): ('post-storage-mongodb', 'FindPosts'),
    ('post-storage-service', 'MmcSetPosts'): ('post-storage-memcached', 'SetPosts'),
    # /wrk2-api/user/register
    ('user-service', 'MongoFindUser'): ('user-mongodb', 'FindUser'),
    ('user-service', 'MongoInsertUser'): ('user-mongodb', 'InsertUser'),
    ('social-graph-service', 'MongoInsertUser'): ('social-graph-mongodb', 'InsertUser'),
    # /get-media
    ('media-frontend', 'MongoGetMedia'): ('media-mongodb', 'GetMedia'),
    # /wrk2-api/user/follow
    ('social-graph-service', 'MongoUpdateFollower'): ('social-graph-mongodb', 'UpdateFollower'),
    ('social-graph-service', 'MongoUpdateFollowee'): ('social-graph-mongodb', 'UpdateFollowee'),
    ('social-graph-service', 'RedisUpdate'): ('social-graph-redis', 'Update'),
    # /wrk2-api/user/unfollow
    ('social-graph-service', 'MongoDeleteFollower'): ('social-graph-mongodb', 'DeleteFollower'),
    ('social-graph-service', 'MongoDeleteFollowee'): ('social-graph-mongodb', 'DeleteFollowee'),
    ('social-graph-service', 'RedisUpdate'): ('social-graph-redis', 'Update'),
}


def get_duration(span, traceMap):
    duration = 0.
    for log in span['logs']:
        duration += (log if type(log) != list else max(_offset + get_duration(traceMap[_spanID], traceMap) for _offset, _spanID in log))
    return int(duration)


if __name__ == '__main__':
    performance_before, performance_after = [], []
    for trace in traces:
        trace = trace[1:] if 'media' in api_of_interest else trace[2:]

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
            if (serviceName, operationName) in mappings:
                (serviceName, operationName) = mappings[(serviceName, operationName)]
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
                    cluster_endTime = max(spanID2dict[_spanID]['startTime'] + spanID2dict[_spanID]['duration'] for _offset, _spanID in cluster)
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
                time_ptr = cluster_startTime + max(_offset + spanID2dict[_spanID]['duration'] for _offset, _spanID in cluster)
            if len(children) > 0:
                logs.append(span['startTime'] + span['duration'] - time_ptr)
            else:
                logs.append(span['duration'])

            _span = {'spanID': spanID, 'operationName': operationName, 'serviceName': serviceName, 'logs': logs}
            _trace.append(_span)
            _traceMap[spanID] = _span
            print(spanID, operationName, serviceName, logs)

        groundtruth = trace[0]['duration']
        estimation = get_duration(_trace[0], _traceMap)
        performance_before.append(groundtruth * 1e-3)
        for parentSpan in _trace:
            parentService = parentSpan['serviceName']
            for i, log in enumerate(parentSpan['logs']):
                if type(log) == list:
                    is_intercloud = False
                    childService = None
                    for _, childSpan in log:
                        childService = _traceMap[childSpan]['serviceName']
                        if (parentService in cloud_components) != (childService in cloud_components):
                            is_intercloud = True
                            break
                    if is_intercloud:
                        request_bytes = data_footprint[api_of_interest][(parentService, childService)]['request']
                        response_bytes = data_footprint[api_of_interest][(parentService, childService)]['response']
                        parentSpan['logs'][i-1] += (rtt // 2 + request_bytes * microseconds_per_byte)
                        parentSpan['logs'][i+1] += (rtt // 2 + response_bytes * microseconds_per_byte)

        performance_after.append(get_duration(_trace[0], _traceMap) * 1e-3)

    plt.subplot(1, 2, 1)
    plt.title('Mean: %.2fms | 50th: %.2fms | 90th: %.2fms\n95th: %.2fms | 99th: %.2fms' % (
        np.mean(performance_before), np.quantile(performance_before, q=.50), np.quantile(performance_before, q=.90),
        np.quantile(performance_before, q=.95), np.quantile(performance_before, q=.99)
    ))
    plt.hist(performance_before)
    plt.subplot(1, 2, 2)
    plt.title('Mean: %.2fms | 50th: %.2fms | 90th: %.2fms\n95th: %.2fms | 99th: %.2fms' % (
        np.mean(performance_after), np.quantile(performance_after, q=.50), np.quantile(performance_after, q=.90),
        np.quantile(performance_after, q=.95), np.quantile(performance_after, q=.99)
    ))
    plt.hist(performance_after)
    plt.show()