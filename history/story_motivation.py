import itertools
from tqdm import tqdm
from lib_cost import CostEstimator
from lib_performance import PerformanceEstimator
from core.application import PlacementPlan
from constants import *
from core.experiment import Experiment
exp = Experiment(path='experiments/story/cadvisor+istio.json')
from matplotlib import pyplot as plt
import numpy as np
import pickle
plt.style.use('ggplot')


with open('./experiments/story/telemetry.pkl', 'rb') as f:
    data = pickle.load(f)
timestamps = data['timestamps'][:120*4]
components = {k: v for k, v in data['components'].items() if k not in ('url-shorten-memcached', 'media-memcached')}
CPU_LIMIT = 4
edges = {k: (sum(v['request']) + sum(v['response'])) * 1e-6 for k, v in data['edges'].items()}
component2cpu = {k: v['cpu'][997] for k, v in components.items()}
perf = PerformanceEstimator(experiment_id='202207302259_202207310221')
cost = CostEstimator()


APIs = ['/wrk2-api/post/compose', '/wrk2-api/home-timeline/read', '/wrk2-api/user-timeline/read',
        '/get-media', '/upload-media',
        '/wrk2-api/user/follow', '/wrk2-api/user/unfollow', '/wrk2-api/user/login', '/wrk2-api/user/register']

# Naive approach (offloading the busiest components)
plan_naive = {'home-timeline-redis', 'nginx-thrift', 'write-home-timeline-service', 'post-storage-service', 'media-frontend', 'compose-post-service', 'text-service', 'user-timeline-service', 'user-mention-service'}
plan_traffic = {"url-shorten-service", "compose-post-redis", "url-shorten-mongodb", "write-home-timeline-service", "nginx-thrift", "user-service", "post-storage-memcached", "home-timeline-service", "media-service", "social-graph-mongodb", "home-timeline-redis", "text-service", "social-graph-service", "user-timeline-redis", "compose-post-service", "user-timeline-service", "write-home-timeline-rabbitmq", "unique-id-service", "post-storage-service", "user-timeline-mongodb", "social-graph-redis"}
plan_ours = {component for component in components if component not in {'media-frontend', 'media-mongodb', 'post-storage-mongodb', 'user-mongodb'}}
perf_results = perf.estimate(plan_naive, detailed=True)
# print('Naive  : USD %.2f per day' % (cost.estimate(plan=PlacementPlan(mapping={
#     c: [PlacementPlan.ONPREM, PlacementPlan.CLOUD][c in plan_naive] for c in exp.msvcs
# }, exp=exp)) / 7))
# print('Traffic: USD %.2f per day' % (cost.estimate(plan=PlacementPlan(mapping={
#     c: [PlacementPlan.ONPREM, PlacementPlan.CLOUD][c in plan_traffic] for c in exp.msvcs
# }, exp=exp)) / 7))
print('Traffic: USD %.2f per day' % (cost.estimate(plan=PlacementPlan(mapping={
    c: [PlacementPlan.ONPREM, PlacementPlan.CLOUD][c in plan_ours] for c in exp.msvcs
}, exp=exp)) / 7))
exit()
perf_benign = [np.mean([tup[0] for tup in perf_results[api]]) for api in APIs]
perf_naive = [np.mean([tup[1] for tup in perf_results[api]]) for api in APIs]
perf_results = perf.estimate(plan_traffic, detailed=True)
perf_traffic = [np.mean([tup[1] for tup in perf_results[api]]) for api in APIs]
perf_results = perf.estimate(plan_ours, detailed=True)
perf_ours = [np.mean([tup[1] for tup in perf_results[api]]) for api in APIs]

x = np.arange(len(API2ID))  # the label locations
width = 0.20  # the width of the bars

fig, ax = plt.subplots()
rects1 = ax.bar(x - width, perf_benign, width, label='Men')
# rects2 = ax.bar(x, perf_naive, width, label='Women')
rects3 = ax.bar(x , perf_traffic, width, label='Women')
rects4 = ax.bar(x + width, perf_ours, width, label='Women')

# Add some text for labels, title and custom x-axis tick labels, etc.
ax.set_ylabel('Scores')
ax.set_title('Scores by group and gender')
ax.set_xticks(x, [READABLE_NAME[api] for api in APIs])
# ax.set_ylim(0, 200)
ax.bar_label(rects1, padding=3)
ax.bar_label(rects3, padding=3)
# ax.bar_label(rects3, padding=3)
ax.bar_label(rects4, padding=3)

fig.tight_layout()

plt.show()