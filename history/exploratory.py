import os
import pickle

import matplotlib.pyplot as plt

root_dir = './experiments/202207012101_202207012350'
# with open(os.path.join(root_dir, 'trace_ids.pkl'), 'rb') as f:
#     traceID = pickle.load(f)

API2durations = {}


for fname in sorted(os.listdir(os.path.join(root_dir, 'traces')), key=lambda x: int(x.split('_')[0])):
    print(fname)
    exit()
    fpath = os.path.join(root_dir, 'traces', fname)

    with open(fpath, 'rb') as f:
        data = pickle.load(f)

    for traceID, trace in data.items():
        api = trace[0]['operationName'].split('/')[-1]
        # print(trace[0]['operationName'].split('/')[-1])
        # print(trace[0]['duration'])
        if api not in API2durations:
            API2durations[api] = []
        API2durations[api].append(int(trace[0]['duration']) * 1e-3)
        if api == 'upload-media':
            print(api)
            for span in trace:
                print(span)
            exit()
for api, durations in API2durations.items():
    plt.title(api)
    plt.hist(durations)
    plt.xlabel('Duration (ms)')
    plt.ylabel('Frequency')
    plt.show()
exit()