from matplotlib import pyplot as plt
import numpy as np
import json


with open('data/20220617-metrics.json') as f:
    data = json.load(f)

xs = data['timestamps']
t_now = 10 * 60 // 5

plt.figure(figsize=(12, 8))
plt.subplot(4, 2, 1)
key = 'cpu'
ys = [v[key] for k, v in data['components'].items() if key in v]
plt.stackplot(xs, *ys)
plt.ylabel('CPU (cores)')
plt.axvline(x=xs[t_now], linestyle='--')
plt.xlim([min(xs), max(xs)])

plt.subplot(4, 2, 3)
key = 'memory'
ys = [[g * 1e-9 for g in v[key]] for k, v in data['components'].items() if key in v]
plt.stackplot(xs, *ys)
plt.ylabel('Memory (GiB)')
plt.axvline(x=xs[t_now], linestyle='--')
plt.xlim([min(xs), max(xs)])

plt.subplot(4, 2, 5)
key = 'traffic-in'
ys = [[g * 1e-6 for g in v[key]] for k, v in data['components'].items() if key in v]
plt.stackplot(xs, *ys)
plt.ylabel('Traffic-in (MiB/sec)')
plt.axvline(x=xs[t_now], linestyle='--')
plt.xlim([min(xs), max(xs)])

plt.subplot(4, 2, 7)
key = 'traffic-out'
ys = [[g * 1e-6 for g in v[key]] for k, v in data['components'].items() if key in v]
plt.stackplot(xs, *ys)
plt.ylabel('Traffic-out (MiB/sec)')
plt.axvline(x=xs[t_now], linestyle='--')
plt.xlim([min(xs), max(xs)])



plt.subplot(4, 2, 2)
key = 'disk-usage'
ys = [v[key] for k, v in data['components'].items() if key in v]
plt.stackplot(xs, *ys)
plt.ylabel('Disk Usage (GiB)')
plt.axvline(x=xs[t_now], linestyle='--')
plt.xlim([min(xs), max(xs)])

plt.subplot(4, 2, 4)
ys = [np.asarray(v['write-iops']) + np.asarray(v['read-iops']) for k, v in data['components'].items() if 'write-iops' in v]
plt.stackplot(xs, *ys)
plt.ylabel('IOPS')
plt.axvline(x=xs[t_now], linestyle='--')
plt.xlim([min(xs), max(xs)])

plt.tight_layout()
plt.show()