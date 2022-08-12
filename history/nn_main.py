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


theta_init = np.full(fill_value=100, shape=(len(flattened_ID),))
res = least_squares(fun, theta_init, bounds=(0, np.inf), verbose=0)

print('')
edge_of_interest = ('istio-ingressgateway', 'nginx-thrift')
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
plt.show()

