import numpy as np
from matplotlib import pyplot as plt
from constants import *
import pickle

########################################################################################################################
EXPERIMENT_ID = '202208012125_202208012245'
########################################################################################################################
with open('./experiments/%s/02_exporter-istio.pkl' % EXPERIMENT_ID, 'rb') as o:
    xs, edges = pickle.load(o)
with open('./experiments/%s/04_network-footprint-learning.pkl' % '202207302259_202207310221', 'rb') as f:
    data_footprint = pickle.load(f)
with open('./experiments/%s/03_trace-to-traffic.pkl' % EXPERIMENT_ID, 'rb') as o:
    X = pickle.load(o)
id2ts = {}
with open('./workloads/footprint.txt', 'r') as f:
    for line in f.readlines():
        line = line.strip().split(',')
        _id = int(line[0])
        _ts = int(float(line[1]))
        if _id not in id2ts:
            id2ts[_id] = _ts

timestamp_interval = {
    '/wrk2-api/post/compose': (id2ts[2], id2ts[3]),
    '/wrk2-api/user-timeline/read': (id2ts[3], id2ts[4]),
    '/wrk2-api/home-timeline/read': (id2ts[4], id2ts[5]),
    '/wrk2-api/user/follow': (id2ts[5], id2ts[6]),
    '/wrk2-api/user/unfollow': (id2ts[6], id2ts[7]),
    '/wrk2-api/user/register': (id2ts[7], id2ts[8]),
    '/wrk2-api/user/login': (id2ts[8], id2ts[9]),
    '/get-media': (id2ts[4], id2ts[5]),
    '/upload-media': (id2ts[2], id2ts[3]),
}

for api in API2EDGES:#['/wrk2-api/user/login']:
    print('==== API %s ====' % api)
    errors = []
    for edge in API2EDGES[api]:
        print('Edge: %s' % str(edge))

        start_ts, end_ts = timestamp_interval[api]
        start_ind = np.argmax(xs >= start_ts) + 24
        end_ind = np.argmax(xs >= end_ts) - 1 - 12
        _X = X[start_ind:end_ind]
        certain = list(_X.sum(axis=0)).count(0) == 8
        if certain:
            num_calls = _X[:, API2ID[api]]
            real_request = np.mean(edges[edge]['request'][start_ind:end_ind] / num_calls)
            real_response = np.mean(edges[edge]['response'][start_ind:end_ind] / num_calls)
            est_request = data_footprint[api][edge]['request']
            est_response = data_footprint[api][edge]['response']
            print('  > Request : %.2f bytes <-> %.2f bytes' % (real_request, est_request))
            print('  > Response: %.2f bytes <-> %.2f bytes' % (real_response, est_response))
            errors.append(abs(est_request - real_request) / real_request)
            errors.append(abs(est_response - real_response) / real_response)
        else:
            print('  > UNCERTAIN')
    print(np.mean(errors) * 100)

exit()


plt.plot(edges[('compose-post-service', 'compose-post-redis')]['request'])
plt.show()