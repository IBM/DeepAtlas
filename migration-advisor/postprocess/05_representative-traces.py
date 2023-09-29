from constants import API2ID
from tqdm import tqdm
import random
import pickle
import os
import sys


########################################################################################################################
EXPERIMENT_ID = sys.argv[1]
NUM_TRACES_PER_API = 100
########################################################################################################################

trace_root = './experiments/%s/traces' % EXPERIMENT_ID
trace_fnames = sorted(os.listdir(trace_root), key=lambda fname: int(fname.split('_')[0]))

repr_locations = {api: [] for api in API2ID}
for fname in tqdm(trace_fnames):
    fpath = os.path.join(trace_root, fname)
    with open(fpath, 'rb') as f:
        data = pickle.load(f)
    for traceID, trace in data.items():
        repr_locations[trace[0]['operationName']].append((fpath, traceID))

repr_traces = {api: [] for api in API2ID}
pbar = tqdm(repr_locations.items())
for api, locations in pbar:
    random.shuffle(locations)
    for i, (fpath, traceID) in enumerate(locations[:NUM_TRACES_PER_API]):
        pbar.set_description('%d/%d' % (i+1, NUM_TRACES_PER_API))
        with open(fpath, 'rb') as f:
            data = pickle.load(f)
        repr_traces[api].append(data[traceID])

with open('./experiments/%s/05_representative-traces.pkl' % EXPERIMENT_ID, 'wb') as o:
    pickle.dump(repr_traces, o)
