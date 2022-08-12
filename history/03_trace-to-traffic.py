from constants import API2ID
from tqdm import tqdm
import numpy as np
import pickle
import os


########################################################################################################################
EXPERIMENT_ID = '202207302259_202207310221'
########################################################################################################################

trace_root = './experiments/%s/traces' % EXPERIMENT_ID
trace_fnames = sorted(os.listdir(trace_root), key=lambda fname: int(fname.split('_')[0]))
assert os.path.exists('./experiments/%s/02_exporter-istio.pkl' % EXPERIMENT_ID), 'Run 02_exporter-istio.py first!'
with open('./experiments/%s/02_exporter-istio.pkl' % EXPERIMENT_ID, 'rb') as o:
    xs, edges = pickle.load(o)

# Create a numpy array with timestamp and operation ID for generating buckets
ts_op = []
for fname in tqdm(trace_fnames):
    fpath = os.path.join(trace_root, fname)
    with open(fpath, 'rb') as f:
        data = pickle.load(f)
    for trace in data.values():
        startTime = trace[0]['startTime'] * 1e-6
        operationId = API2ID[trace[0]['operationName']]
        ts_op.append((startTime, operationId))
ts_op = np.asarray(ts_op)

# Generate the API traffic per 1-minute bucket
X = []
for x in tqdm(xs):
    calls = ts_op[(x - ts_op[:, 0] >= 0.) & (x - ts_op[:, 0] < 60.), 1]
    X.append([np.sum(calls == api) for api in range(len(API2ID))])
X = np.asarray(X)

with open('./experiments/%s/03_trace-to-traffic.pkl' % EXPERIMENT_ID, 'wb') as o:
    pickle.dump(X, o)
