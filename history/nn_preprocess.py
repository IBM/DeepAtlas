from sklearn.preprocessing import MinMaxScaler
from scipy.optimize import least_squares
from tqdm import tqdm
import matplotlib.pyplot as plt
import numpy as np
import pickle
import os

with open('./experiments/202207221540_202207221911/prometheus-istio.pkl', 'rb') as f:
    timestamps, edges = pickle.load(f)
    edges_keys = list(edges.keys())
with open('./experiments/202207221540_202207221911/X_mapping.pkl', 'rb') as f:
    X, API2id = pickle.load(f)
    id2API = {i: API for API, i in API2id.items()}


API2edges = {
    '/upload-media': (
        ('istio-ingressgateway', 'media-frontend'),
        ('media-frontend', 'media-mongodb')
    ),
    '/get-media': (
        ('istio-ingressgateway', 'media-frontend'),
        ('media-frontend', 'media-mongodb')
    ),

    '/wrk2-api/user/follow': (
        ('istio-ingressgateway', 'nginx-thrift'),
        ('nginx-thrift', 'social-graph-service'),
            ('social-graph-service', 'social-graph-mongodb'),
            ('social-graph-service', 'social-graph-redis')
    ),
    '/wrk2-api/user/unfollow': (
        ('istio-ingressgateway', 'nginx-thrift'),
        ('nginx-thrift', 'social-graph-service'),
            ('social-graph-service', 'social-graph-mongodb'),
            ('social-graph-service', 'social-graph-redis')
    ),

    '/wrk2-api/user/login': (
        ('istio-ingressgateway', 'nginx-thrift'),
        ('nginx-thrift', 'user-service'),
            ('user-service', 'user-memcached'),
            ('user-service', 'user-mongodb')
    ),
    '/wrk2-api/user/register': (
        ('istio-ingressgateway', 'nginx-thrift'),
        ('nginx-thrift', 'user-service'),
            ('user-service', 'user-mongodb'),
            ('user-service', 'social-graph-service'),
                ('social-graph-service', 'social-graph-mongodb')
    ),

    '/wrk2-api/home-timeline/read': (
        ('istio-ingressgateway', 'nginx-thrift'),
        ('nginx-thrift', 'home-timeline-service'),
            ('home-timeline-service', 'home-timeline-redis'),
            ('home-timeline-service', 'post-storage-service'),
                ('post-storage-service', 'post-storage-mongodb'),
                ('post-storage-service', 'post-storage-memcached')
    ),
    '/wrk2-api/user-timeline/read': (
        ('istio-ingressgateway', 'nginx-thrift'),
        ('nginx-thrift', 'user-timeline-service'),
            ('user-timeline-service', 'user-timeline-redis'),
            ('user-timeline-service', 'post-storage-service'),
                ('post-storage-service', 'post-storage-mongodb'),
                ('post-storage-service', 'post-storage-memcached'),
            ('user-timeline-service', 'user-timeline-mongodb')
    ),

    '/wrk2-api/post/compose': (
        ('istio-ingressgateway', 'nginx-thrift'),
        ('nginx-thrift', 'user-service'),
            ('user-service', 'compose-post-service'),

        ('nginx-thrift', 'unique-id-service'),
            ('unique-id-service', 'compose-post-service'),

        ('nginx-thrift', 'media-service'),
            ('media-service', 'compose-post-service'),

        ('nginx-thrift', 'text-service'),
            ('text-service', 'user-mention-service'),
                ('user-mention-service', 'user-memcached'),
                ('user-mention-service', 'user-mongodb'),
                ('user-mention-service', 'compose-post-service'),
            ('text-service', 'url-shorten-service'),
                ('url-shorten-service', 'url-shorten-mongodb'),
                ('url-shorten-service', 'compose-post-service'),
            ('text-service', 'compose-post-service'),

        ('compose-post-service', 'post-storage-service'),
            ('post-storage-service', 'post-storage-mongodb'),
        ('compose-post-service', 'user-timeline-service'),
            ('user-timeline-service', 'user-timeline-mongodb'),
            ('user-timeline-service', 'user-timeline-redis'),
        ('compose-post-service', 'compose-post-redis'),
        ('compose-post-service', 'write-home-timeline-rabbitmq'),
            ('write-home-timeline-service', 'write-home-timeline-rabbitmq'),
            ('write-home-timeline-service', 'home-timeline-redis'),
            ('write-home-timeline-service', 'social-graph-service'),
                ('social-graph-service', 'social-graph-redis'),
                ('social-graph-service', 'social-graph-mongodb'),
    ),
}


flattened = []
flattened_ID = []
for API, _es in API2edges.items():
    es = list(filter(lambda x: x in edges_keys, _es))
    flattened += list(es)
    flattened_ID += [API2id[API]] * len(es)
flattened_ID = np.asarray(flattened_ID)
print('Total number of parameters: %d' % len(flattened_ID))

Y, relevant_params, relevant_APIs = [], [], []
for edge in edges_keys:
    Y.append(edges[edge]['request'])
    relevant_params.append([ind for ind in range(len(flattened)) if flattened[ind] == edge])
    relevant_APIs.append([flattened_ID[ind] for ind in range(len(flattened)) if flattened[ind] == edge])
    print('%s' % str(edge))
    for r1, r2 in enumerate(relevant_APIs[-1]):
        print('   > API #%d (%s): Param #%d' % (r2, id2API[r2], relevant_params[-1][r1]))
Y = np.asarray(Y).transpose()

relevant_params = np.asarray(relevant_params)
relevant_APIs = np.asarray(relevant_APIs)

X_train, Y_train = X[:2000], Y[:2000]
X_test, Y_test = X[2000:], Y[2000:]


def s(theta, t):
    # Output Size: (1000, 40)
    ret = []
    for eid, edge in enumerate(edges_keys):
        xx = t[:, relevant_APIs[eid]]
        tt = theta[relevant_params[eid]][np.newaxis, :]
        rr = np.sum((xx * tt), axis=1)
        ret.append(rr)
    ret = np.asarray(ret).transpose()
    return ret


def fun(theta):
    return (s(theta, X_train) - Y_train).flatten()


theta_init = np.full(fill_value=0.5, shape=(len(flattened_ID),))
res = least_squares(fun, theta_init, bounds=(0, np.inf), verbose=0)

print('')
edge_of_interest = ('istio-ingressgateway', 'media-frontend')
for edge_of_interest in edges_keys:
    api2bytes = {}
    for i in range(len(res.x)):
        if flattened[i] == edge_of_interest:
            assert id2API[flattened_ID[i]] not in api2bytes, id2API[flattened_ID[i]]
            api2bytes[id2API[flattened_ID[i]]] = res.x[i]
            print('%s: %f bytes' % (id2API[flattened_ID[i]], res.x[i]))

    print(X_test.shape)
    Y_t = []
    for t in range(len(X_test)):
        b = 0
        for idd, apii in id2API.items():
            if apii in api2bytes:
                b += X_test[t][idd] * api2bytes[apii]
        Y_t.append(b)
    plt.clf()
    plt.title(edge_of_interest)
    plt.plot(Y_test[:, edges_keys.index(edge_of_interest)], label='real')
    plt.plot(Y_t, label='est')
    plt.legend()
    plt.savefig('./tmp/%s.png' % '_'.join(edge_of_interest))


exit()


trace_root = './experiments/202207221540_202207221911/traces'
trace_fnames = sorted(os.listdir(trace_root), key=lambda x: int(x.split('_')[0]))
with open('./experiments/202207221540_202207221911/prometheus.pkl', 'rb') as f:
    prometheus = pickle.load(f)
    components = prometheus['components']
C = {c: False for c in components}
API2edge = {}
for fid, fname in enumerate(trace_fnames):
    fpath = os.path.join(trace_root, fname)
    with open(fpath, 'rb') as f:
        data = pickle.load(f)
    print(fid, len(data))

    for trace_id, trace in data.items():
        API = trace[0]['operationName']
        if API not in API2edge:
            API2edge[API] = set()
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

        spanID2serviceName = {}
        for span in trace:
            spanID = span['spanID']
            operationName = span['operationName']
            serviceName = list(filter(lambda x: x['key'] == 'container.name', span['process']['tags']))[0]['value']
            if (serviceName, operationName) in mappings:
                (serviceName, operationName) = mappings[(serviceName, operationName)]
            for bl in ['Mongo', 'Mmc', 'Redis']:
                if bl in operationName:
                    print("('%s', '%s')" % (serviceName, operationName))
                    print('[%s] Alert! %s in %s' % (API, bl, operationName))
                    exit()
            assert serviceName in components, '%s not in components' % serviceName
            spanID2serviceName[spanID] = serviceName

            if len(span['references']) > 0:
                edge = (spanID2serviceName[span['references'][0]['spanID']], serviceName)
                if edge[0] == edge[1]:
                    continue
                API2edge[API].add(edge)

# TODO:
API2edge['/wrk2-api/post/compose'].add(('compose-post-service', 'compose-post-redis'))
API2edge['/wrk2-api/post/compose'].add(('compose-post-service', 'write-home-timeline-rabbitmq'))
API2edge['/wrk2-api/post/compose'].add(('write-home-timeline-rabbitmq', 'write-home-timeline-service'))

for API, edges in API2edge.items():
    print(API, edges)
exit()
with open('./experiments/202207221540_202207221911/prometheus-istio.pkl', 'rb') as f:
    timestamps, edges = pickle.load(f)

with open('./experiments/202207221540_202207221911/X_mapping.pkl', 'rb') as f:
    X, API2id = pickle.load(f)

Y, Y_mapping = [], []
for edge, data in edges.items():
    Y.append(data['request'])
    Y_mapping.append('_'.join(edge) + '_' + 'request')
    Y.append(data['response'])
    Y_mapping.append('_'.join(edge) + '_' + 'response')
Y = np.asarray(Y).transpose()

print('X.shape: %s' % str(X.shape))  # (num_of_points, API_calls)
print('Y.shape: %s' % str(Y.shape))  # (num_of_points, transferred_bytes)

X_train, Y_train, timestamps_train = X[1000:2000], Y[1000:2000], timestamps[1000:2000]
X_test, Y_test, timestamps_test = X[2000:2500], Y[2000:2500], timestamps[2000:2500]

theta = np.ones(shape=(X.shape[1], Y.shape[1]))  # (num_APIs, num_edges)

print(theta)
exit()

X = X[1000:2000]
Y = Y[1000:2000]

scaler = MinMaxScaler()
scaler.fit(Y)
print(Y.shape)
Y = scaler.transform(Y)

# plt.stackplot(range(len(X)), *[Y[:, i] for i in range(Y.shape[1])])
# plt.show()
# print('X.shape: %s' % str(X.shape))
# print('Y.shape: %s' % str(Y.shape))
# exit()
E_shape = (len(API_mapping), len(edges) * 2)
E = np.reshape(res.x, newshape=E_shape)
E = scaler.inverse_transform(E)
for i, api in enumerate(API_mapping):
    print('===== %s =====' % api)
    for j, y in enumerate(Y_mapping):
        print('   > %s | %f bytes' % (y, E[i, j]))
print(E.shape)

exit()


def s(theta, t):
    ret = np.matmul(t, np.reshape(theta, newshape=E_shape)) / 60.
    return np.array(ret)


def fun(theta):
    return (s(theta, X) - Y).flatten()


res2 = least_squares(fun, E, bounds=(0, np.inf), verbose=2, ftol=1e-4)
with open('./tmp.pkl', 'wb') as f:
    pickle.dump(res2, f)
print(res2)
exit()

exit()
trace_root = './experiments/202207221540_202207221911/traces'
trace_fnames = sorted(os.listdir(trace_root), key=lambda x: int(x.split('_')[0]))
with open('./experiments/202207221540_202207221911/buckets.pkl', 'rb') as f:
    buckets = pickle.load(f)
with open('./experiments/202207221540_202207221911/trace_api.pkl', 'rb') as f:
    apis = pickle.load(f)
    feature_space = {'/wrk2-api/user/register': 0,
                     '/wrk2-api/user/follow': 1,
                     '/wrk2-api/user/unfollow': 2,
                     '/get-media': 3,
                     '/wrk2-api/home-timeline/read': 4,
                     '/wrk2-api/post/compose': 5,
                     '/upload-media': 6,
                     '/wrk2-api/user-timeline/read': 7,
                     '/wrk2-api/user/login': 8}

X = []
for ix, x in enumerate(xs):
    fv = [0 for _ in range(len(feature_space))]
    for trace_id in buckets[ix]:
        fv[feature_space[apis[trace_id]]] += 1
    X.append(fv)
X = np.asarray(X)

with open('./experiments/202207221540_202207221911/X_mapping.pkl', 'wb') as f:
    pickle.dump((X, feature_space), f)

exit()

with open('./experiments/202207221540_202207221911/trace_meta.pkl', 'rb') as f:
    T = pickle.load(f)
    T1, T2, T3 = zip(*T)
    T1 = np.asarray(T1)
    T2 = np.asarray(T2)

buckets = []
pbar = tqdm(xs)
for x in pbar:
    mask = (x - T1 >= 0.) & (x - T1 < 60.)
    buckets.append(list(T2[mask]))
    pbar.set_description('Length: %d' % mask.sum())

with open('./experiments/202207221540_202207221911/buckets.pkl', 'wb') as f:
    pickle.dump(buckets, f)

#
exit()
T = {}
for fname in tqdm(trace_fnames):
    fpath = os.path.join(trace_root, fname)
    with open(fpath, 'rb') as f:
        data = pickle.load(f)
    for traceID, v in data.items():
        operationName = v[0]['operationName']
        T[traceID] = operationName
with open('./experiments/202207221540_202207221911/trace_api.pkl', 'wb') as f:
    pickle.dump(T, f)
