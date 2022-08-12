import matplotlib.pyplot as plt
import numpy as np
import pickle
from datetime import datetime
plt.style.use('ggplot')

with open('./experiments/story/telemetry.pkl', 'rb') as f:
    data = pickle.load(f)
timestamps = data['timestamps']
components = data['components']
edges = data['edges']

X_cpu = []
labels = []
for k, v in components.items():
    X_cpu.append(v['cpu'])
    labels.append(k)

import seaborn as sns

plt.figure(figsize=(6, 3), dpi=150)
plt.stackplot(range(len(timestamps)), *X_cpu, labels=labels, colors=sns.color_palette("flare", len(X_cpu)))
# plt.xlabel('Timeline')
plt.ylabel('CPU Utilization (Cores)')
# plt.axhline(y=4, linestyle='--')
xs_loc = [0, 120, 240, 360, 480]
xs_lab = [' ', ' ', ' ', ' ', ' ']
plt.xticks(xs_loc, xs_lab)
plt.xlim(0, 480)
plt.ylim([0, 11])
plt.tight_layout()
plt.show()
exit()
X_cpu_ = np.sum(X_cpu, axis=0)
print(X_cpu_[997])

max_cpu = []
for component in components:
    max_cpu.append((component, components[component]['cpu'][997]))
max_cpu = sorted(max_cpu, key=lambda x: -x[1])

usage = X_cpu_[997]
a = set()
for c, cpu in max_cpu:
    # print('Offload %s: %f' % (c, cpu))
    # print('  %f -> %f' % (usage, usage-cpu))
    if c in ['media-mongodb', 'user-mongodb', 'post-storage-mongodb']:
        continue
    print(c)
    a.add(c)
    usage = usage - cpu
    if usage < 4:
        break
print(a)