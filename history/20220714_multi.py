import pickle

import numpy as np
from tqdm import tqdm
from matplotlib import pyplot as plt
import os
plt.style.use('ggplot')

root_dir = 'experiments/202207131729_202207141313/traces'
fnames = sorted(os.listdir(root_dir), key=lambda v: int(v.split('_')[0]))

duration = {'login': [],
            'register': [],
            'follow': [],
            'unfollow': []}
for fname in tqdm(fnames):
    fpath = os.path.join(root_dir, fname)
    with open(fpath, 'rb') as f:
        data = pickle.load(f)
    _duration = {'login': [],
                 'register': [],
                 'follow': [],
                 'unfollow': []}
    for trace in data.values():
        api_name = trace[0]['operationName']
        good = False
        if api_name == '/wrk2-api/user/login' and len(trace) == 5:
            good = True
        elif api_name == '/wrk2-api/user/register' and len(trace) == 8:
            good = True
        elif api_name == '/wrk2-api/user/follow' and len(trace) == 7:
            good = True
        elif api_name == '/wrk2-api/user/unfollow' and len(trace) == 7:
            good = True
        if not good:
            continue

        op_name = api_name.split('/')[-1]
        _duration[op_name].append(int(trace[0]['duration']) * 1e-3)
    duration['login'].append(_duration['login'])
    duration['register'].append(_duration['register'])
    duration['follow'].append(_duration['follow'])
    duration['unfollow'].append(_duration['unfollow'])


import matplotlib.pyplot as plt
plt.style.use('ggplot')

duration_login = [np.mean(duration['login'][v]) for v in range(len(duration['login']))]
duration_register = [np.mean(duration['register'][v]) for v in range(len(duration['register']))]
duration_follow = [np.mean(duration['follow'][v]) for v in range(len(duration['follow']))]
duration_unfollow = [np.mean(duration['unfollow'][v]) for v in range(len(duration['unfollow']))]

login_onprem = np.mean([np.mean(duration['login'][v]) for v in [1, 2, 3, 4, 5]])
register_onprem = np.mean([np.mean(duration['login'][v]) for v in [1, 2, 3, 4, 5]])
follow_onprem = np.mean([np.mean(duration['login'][v]) for v in [1, 2, 3, 4, 5]])
unfollow_onprem = np.mean([np.mean(duration['login'][v]) for v in [1, 2, 3, 4, 5]])

latency = 38.5
xs_c1 = [5, 6, 7, 8, 9]
xs_c2 = [10, 11]
login_c1 = login_onprem + latency * 2
login_c2 = login_onprem
login_c3 = login_onprem + latency * 2

register_c1 = register_onprem + latency * 4
register_c2 = register_onprem + latency * 2
register_c3 = register_onprem + latency * 4

follow_c1 = follow_onprem
follow_c2 = follow_onprem + latency * 2
follow_c3 = follow_onprem + latency * 2

unfollow_c1 = unfollow_onprem
unfollow_c2 = unfollow_onprem + latency * 2
unfollow_c3 = unfollow_onprem + latency * 2


plt.plot(duration_login)
plt.xticks(range(len(duration_login)))
plt.show()

segments = [range(1, 6), range(7, 12), range(13, 18), range(19, 24)]

xs = []
for stage, segment in enumerate(segments):
    _xs = list(range(0 if len(xs) == 0 else 1 + max(xs), (0 if len(xs) == 0 else 1 + max(xs)) + len(segment)))
    xs += _xs
    print()
    if stage == 0:
        plt.plot(_xs, [duration_login[i] for i in segment], label='/login', color='tab:red', linewidth=2)
        plt.plot(_xs, [duration_register[i] for i in segment], label='/register', color='tab:orange', linewidth=2)
        plt.plot(_xs, [duration_follow[i] for i in segment], label='/follow', color='tab:green', linewidth=2)
        plt.plot(_xs, [duration_unfollow[i] for i in segment], label='/unfollow', color='tab:blue', linewidth=2)
        print(np.mean([duration_login[i] for i in segment]))
        print(np.mean([duration_register[i] for i in segment]))
        print(np.mean([duration_follow[i] for i in segment]))
        print(np.mean([duration_unfollow[i] for i in segment]))
    else:
        plt.plot(_xs, [duration_login[i] for i in segment], color='tab:red', linewidth=2)
        plt.plot(_xs, [duration_register[i] for i in segment], color='tab:orange', linewidth=2)
        plt.plot(_xs, [duration_follow[i] for i in segment], color='tab:green', linewidth=2)
        plt.plot(_xs, [duration_unfollow[i] for i in segment], color='tab:blue', linewidth=2)

        plt.plot(_xs, [[login_c1, login_c2, login_c3][stage-1]] * len(_xs), linestyle='--', color='tab:red', linewidth=2)
        plt.plot(_xs, [[register_c1, register_c2, register_c3][stage-1]] * len(_xs), linestyle='--', color='tab:orange', linewidth=2)
        plt.plot(_xs, [[follow_c1, follow_c2, follow_c3][stage-1]] * len(_xs), linestyle='--', color='tab:green', linewidth=2)
        plt.plot(_xs, [[unfollow_c1, unfollow_c2, unfollow_c3][stage-1]] * len(_xs), linestyle='--', color='tab:blue', linewidth=2)
        print(np.mean([duration_login[i] for i in segment]), np.mean([[login_c1, login_c2, login_c3][stage-1]] * len(_xs)))
        print(np.mean([duration_register[i] for i in segment]), np.mean([[register_c1, register_c2, register_c3][stage-1]] * len(_xs)))
        print(np.mean([duration_follow[i] for i in segment]), np.mean([[follow_c1, follow_c2, follow_c3][stage-1]] * len(_xs)))
        print(np.mean([duration_unfollow[i] for i in segment]), np.mean([[unfollow_c1, unfollow_c2, unfollow_c3][stage-1]] * len(_xs)))

plt.legend()
plt.xlim([0, len(xs)-1])
plt.ylabel('API-Performance (ms)')
plt.xticks(range(len(xs)), ['07/14\n12:%02d' % i for i in range(len(xs))])
plt.show()
