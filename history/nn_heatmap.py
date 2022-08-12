from matplotlib import pyplot as plt
import numpy as np
import pickle


# with open('./experiments/202207221540_202207221911/traces/200_202207221901.pkl', 'rb') as f:
api_of_interest = '/compose'
with open('./experiments/202207221540_202207221911/traces/11_202207221551.pkl', 'rb') as f:
    traces = list(filter(lambda trace: api_of_interest in trace[0]['operationName'], pickle.load(f).values()))

print('Number of Traces: %d' % len(traces))
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


for trace in traces:
    height, width = 0, -np.inf
    HM = np.zeros((1000, 500000))
    yticks = [None for _ in range(HM.shape[0])]
    yticks_parent = [None for _ in range(HM.shape[0])]
    relationships = {}

    trace = trace[1:] if 'media' in api_of_interest else trace[2:]
    spanID2name = {}
    spanID2period = {}
    spanID2children = {}
    for span in trace:
        operationName = span['operationName'].replace('/wrk2-api/user', '')
        serviceName = list(filter(lambda x: x['key'] == 'container.name', span['process']['tags']))[0]['value']
        if (serviceName, operationName) in mappings:
            (serviceName, operationName) = mappings[(serviceName, operationName)]
        if (serviceName, operationName) == ('compose-post-service', 'InsertUniqueIdToPost'):
            maxDuration = 0
            for _span in trace:
                if _span['operationName'] == 'StorePost' and len(_span['references']) > 0 and _span['references'][0]['spanID'] == span['spanID']:
                    print('hh', _span['startTime'] + _span['duration'])
                    maxDuration = max(maxDuration, _span['startTime'] + _span['duration'] - span['startTime'])
                if _span['operationName'] == 'WriteUserTimeline' and len(_span['references']) > 0 and _span['references'][0]['spanID'] == span['spanID']:
                    maxDuration = max(maxDuration, _span['startTime'] + _span['duration'] - span['startTime'])
            span['duration'] = maxDuration

        start_ind = span['startTime'] - trace[0]['startTime']
        # if serviceName in ['user-service']:
        #     start_ind += int(38.5 / 2 * 1000)
        end_ind = start_ind + span['duration']
        spanID2children[span['spanID']] = []
        for parent in span['references']:
            if parent['spanID'] not in spanID2children:
                continue
            spanID2children[parent['spanID']].append(span['spanID'])

        spanName = '%s@%s' % (operationName, serviceName)
        spanID2period[span['spanID']] = (spanName, start_ind, end_ind)

        spanID2name[span['spanID']] = spanName
        if spanName in yticks:
            row = yticks.index(spanName)
        else:
            row = height
            yticks[row] = spanName
            height += 1
        if len(span['references']) > 0 and span['references'][0]['spanID'] in spanID2name:
            yticks_parent[row] = spanID2name[span['references'][0]['spanID']]
        HM[row, start_ind:end_ind] += 1
        width = max(end_ind, width)
    for spanID, children in spanID2children.items():
        print(spanID2period[spanID][0])
        for childID in children:
            print('   > %s: [%d, %d]' % (spanID2period[childID]))
    print('duration: %d' % trace[0]['duration'])
    base = trace[0]['startTime']
    for span in trace:
        print(span['spanID'], span['startTime'] - base, span['startTime'] + span['duration'] - base, span['duration'])
        print('   > %s, %s' % (span['operationName'], span['process']['serviceName']))
    # break

    HM = HM[:height, :width]
    HM = HM / np.max(HM, axis=1, keepdims=True)
    yticks = yticks[:height]
    yticks = ['(%d) ' % (i + 1) + yticks[i] + ('\nParent: (%d)' % (yticks.index(yticks_parent[i]) + 1) if yticks_parent[i] else '') for i in range(len(HM))]
    plt.figure(figsize=(12, 6))
    plt.title('API: %s' % api_of_interest)
    plt.imshow(HM, aspect='auto', cmap='jet', interpolation='nearest')
    plt.yticks(range(len(yticks)), yticks)
    plt.xlabel('Timeline (microseconds)')
    plt.tight_layout()
    plt.show()
