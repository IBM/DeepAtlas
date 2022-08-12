import pickle

import numpy as np
from tqdm import tqdm
from matplotlib import pyplot as plt
import os
plt.style.use('ggplot')

with open('./tmp.pkl', 'rb') as f:
    xs, duration = pickle.load(f)
duration = list(filter(lambda d: len(d) > 1000, duration))

duration_1 = duration[:7]
xs_1 = range(0, 7)
duration_2 = duration[6:17]
xs_2 = range(6, 17)
duration_3 = duration[16:]
xs_3 = range(16, len(duration))

plt.plot(xs_1, [np.mean(d) * 1e-3 for d in duration_1], color='tab:green')
# plt.axvline(x=6, linestyle=':', color='black')
plt.plot(xs_2, [np.mean(d) * 1e-3 for d in duration_2], color='tab:blue', label='')
plt.plot(xs_2, [1.95 + 38.5 for d in duration_2], color='tab:blue', label='', linestyle='--')
# plt.axvline(x=16, linestyle=':', color='black')
plt.plot(xs_3, [np.mean(d) * 1e-3 for d in duration_3], color='tab:red')
plt.plot(xs_3, [1.95 + 38.5 for d in duration_3], color='tab:red', label='', linestyle='--')
# plt.legend(loc='lower right')
plt.ylabel('API Performance (ms)')
plt.xlabel('Timeline')
plt.title('/login')
plt.xticks(range(len(duration)), ['' for _ in range(len(duration))])
plt.xlim([0, len(duration)-1])
plt.show()




exit()

root_dir = 'experiments/202207131415_202207131611/traces'
fnames = sorted(os.listdir(root_dir), key=lambda v: int(v.split('_')[0]))[26:]

xs = []
duration = []
for fname in tqdm(fnames):
    fpath = os.path.join(root_dir, fname)
    with open(fpath, 'rb') as f:
        data = pickle.load(f)
    _duration = []
    for trace in data.values():
        if len(trace) == 5 and trace[0]['operationName'] == '/wrk2-api/user/login':
            _duration.append(int(trace[0]['duration']))
    xs.append(fname.split('_')[1])
    duration.append(_duration)

with open('./tmp.pkl', 'wb') as f:
    pickle.dump((xs, duration), f)
