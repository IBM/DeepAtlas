import json
from constants import *
import numpy as np


APIs = ['/wrk2-api/post/compose', '/wrk2-api/home-timeline/read',
        '/get-media', '/upload-media',
        '/wrk2-api/user/follow', '/wrk2-api/user/login', '/wrk2-api/user/register']
# API2fname = {
# '/wrk2-api/post/compose': 'compose', '/wrk2-api/home-timeline/read': 'hometimeline',
#         '/get-media': 'getmedia', '/upload-media': 'uploadmedia',
#         '/wrk2-api/user/follow': 'follow', '/wrk2-api/user/login': 'login', '/wrk2-api/user/register': 'register'
# }
#
# xs = []
# xs_err = []
# for API in APIs:
#     with open('api-comparisons/horrible-%s.json' % API2fname[API]) as f:
#         data = json.load(f)
#
#     duration = np.mean([trace['spans'][0]['duration'] for trace in data['data']]) * 1e-3
#     duration_std = np.std([trace['spans'][0]['duration'] for trace in data['data']]) * 1e-3
#     xs.append(duration)
#     xs_err.append(duration_std)
# print(str(xs))
# exit()
from matplotlib import pyplot as plt
plt.style.use('ggplot')

plt.figure(figsize=(8, 4.4), dpi=150)
plt.ylabel('End-to-end Latency (ms)')
x = np.arange(len(APIs))  # the label locations
width = 0.35  # the width of the bars


est1 = [351.16, 164.58, 116.63, 21.38, 49.08, 48.48, 102.93]
real1 = [18.80, 7.43, 4.97, 2.34, 3.14, 2.52, 10.59]

rects1 = plt.bar(x - width/2, real1, width, color='tab:green', label='On-prem')
rects2 = plt.bar(x + width/2, est1, width, color='tab:red', label='Hybrid Cloud: Very Bad Plan')

# Add some text for labels, title and custom x-axis tick labels, etc.
plt.gca().set_xticks(x, [READABLE_NAME[api] for api in APIs])

plt.gca().bar_label(rects1, padding=3)
plt.gca().bar_label(rects2, padding=3)
plt.ylim(0, 360)
plt.legend()
plt.yticks(range(0, 370, 40))
plt.tight_layout()
plt.show()
