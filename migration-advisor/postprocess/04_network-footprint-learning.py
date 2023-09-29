from constants import API2ID, ID2API, API2EDGES
from scipy.optimize import least_squares
import numpy as np
import pickle
import sys

########################################################################################################################
EXPERIMENT_ID = sys.argv[1]
########################################################################################################################

with open('./experiments/%s/02_exporter-istio.pkl' % EXPERIMENT_ID, 'rb') as f:
    timestamps, edges = pickle.load(f)
    edges_keys = list(edges.keys())
with open('./experiments/%s/03_trace-to-traffic.pkl' % EXPERIMENT_ID, 'rb') as f:
    X = pickle.load(f)


########################################################################################################################
flattened_edge, flattened_api = [], []
for api in API2EDGES:
    es = list(filter(lambda x: x in edges_keys, API2EDGES[api]))
    flattened_edge += list(es)
    flattened_api += [API2ID[api]] * len(es)
flattened_api = np.asarray(flattened_api)
print('Total number of parameters: %d' % len(flattened_api))

########################################################################################################################
Y_request, Y_response, relevant_params, relevant_APIs = [], [], [], []
for edge in edges_keys:
    Y_request.append(edges[edge]['request'])
    Y_response.append(edges[edge]['response'])
    relevant_params.append([ind for ind in range(len(flattened_edge)) if flattened_edge[ind] == edge])
    relevant_APIs.append([flattened_api[ind] for ind in range(len(flattened_edge)) if flattened_edge[ind] == edge])
Y_request = np.asarray(Y_request).transpose()
Y_response = np.asarray(Y_response).transpose()

########################################################################################################################
X_train, Y_request_train, Y_response_train = X, Y_request, Y_response


def s(theta, t):
    ret = []
    for eid, edge in enumerate(edges_keys):
        xx = t[:, relevant_APIs[eid]]
        tt = theta[relevant_params[eid]][np.newaxis, :]
        rr = np.sum((xx * tt), axis=1)
        ret.append(rr)
    ret = np.asarray(ret).transpose()
    return ret


def fun_request(theta):
    return (s(theta, X_train) - Y_request_train).flatten()


def fun_response(theta):
    return (s(theta, X_train) - Y_response_train).flatten()


ls_result_request = least_squares(
    fun_request, np.full(fill_value=1, shape=(len(flattened_api),)), bounds=(0, np.inf), verbose=2)
ls_result_response = least_squares(
    fun_response, np.full(fill_value=1, shape=(len(flattened_api),)), bounds=(0, np.inf), verbose=2)

ret = {}
for i in range(len(flattened_api)):
    api = ID2API[flattened_api[i]]
    edge = flattened_edge[i]
    if api not in ret:
        ret[api] = {}
    ret[api][edge] = {'request': ls_result_request.x[i], 'response': ls_result_response.x[i]}

with open('./experiments/%s/04_network-footprint-learning.pkl' % EXPERIMENT_ID, 'wb') as f:
    pickle.dump(ret, f)
