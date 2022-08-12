from matplotlib import pyplot as plt
import pickle
import os

fnames = sorted(os.listdir('./data/20220617-traces'))

timestamps = {}
trace_uniqueness = set()
for fname in fnames:
    with open(os.path.join('./data/20220617-traces', fname), 'rb') as f:
        data = pickle.load(f)

        for trace in data:
            assert trace['traceID'] not in trace_uniqueness, 'Uniqueness check failed. %s' % trace['traceID']
            trace_uniqueness.add(trace['traceID'])
            if int(trace['spans'][0]['startTime'] * 1e-6) not in timestamps:
                timestamps[int(trace['spans'][0]['startTime'] * 1e-6)] = 0
            timestamps[int(trace['spans'][0]['startTime'] * 1e-6)] += 1

xs = list(timestamps.keys())
ys = list([timestamps[k] for k in xs])

plt.plot(xs, ys)
plt.show()
# plt.show()