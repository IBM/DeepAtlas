import matplotlib.pyplot as plt
from constants import *
import numpy as np
plt.style.use('ggplot')

APIs = ['/wrk2-api/post/compose', '/wrk2-api/home-timeline/read',
        '/get-media', '/upload-media',
        '/wrk2-api/user/follow', '/wrk2-api/user/login', '/wrk2-api/user/register']


plt.figure(figsize=(8, 5.8), dpi=150)
plt.subplot(2, 1, 1)
plt.ylabel('End-to-end Latency (ms)')
plt.title('Best Performance Plan')
x = np.arange(len(APIs))  # the label locations
width = 0.35  # the width of the bars

real1 = [63.4, 17.8, 5.1, 2.3, 4.0, 3.9, 57.9]  #best
est1 = [63.7, 16.2, 4.5, 1.8, 2.4, 1.8, 55.2]

rects1 = plt.bar(x - width/2, real1, width, color='tab:green')
rects2 = plt.bar(x + width/2, est1, width, color='tab:brown')

# Add some text for labels, title and custom x-axis tick labels, etc.
plt.gca().set_xticks(x, [READABLE_NAME[api] for api in APIs])

plt.gca().bar_label(rects1, padding=3)
plt.gca().bar_label(rects2, padding=3)
plt.ylim(0, 140)
plt.yticks(range(0, 150, 20))

plt.subplot(2, 1, 2)
plt.ylabel('End-to-end Latency (ms)')
plt.title('Worst Performance Plan')
x = np.arange(len(APIs))  # the label locations
width = 0.35  # the width of the bars

real2 = [134.2, 38.2, 4.9, 2.3, 26.7, 2.6, 33.8]
est2 = [136.4, 38.9, 4.5, 1.9, 25.1, 1.8, 32.6]

rects1 = plt.bar(x - width/2, real2, width, color='tab:green')
rects2 = plt.bar(x + width/2, est2, width, color='tab:brown')
real = real1 + real2
est = est1 + est2
print(np.mean([abs(real[i] - est[i]) / real[i] for i in range(len(real))]))
# Add some text for labels, title and custom x-axis tick labels, etc.
plt.gca().set_xticks(x, [READABLE_NAME[api] for api in APIs])

plt.gca().bar_label(rects1, padding=3)
plt.gca().bar_label(rects2, padding=3)
plt.ylim(0, 140)
plt.yticks(range(0, 150, 20))
plt.tight_layout()
plt.savefig('performance-plan.png')
plt.show()