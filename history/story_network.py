import matplotlib.pyplot as plt

from lib_performance import PerformanceEstimator
from lib_cost import CostEstimator
from core.application import PlacementPlan
from core.experiment import Experiment
from tqdm import tqdm
import numpy as np
import itertools
import pickle

with open('./experiments/story/telemetry.pkl', 'rb') as f:
    data = pickle.load(f)
timestamps = data['timestamps'][:120*4]
components = {k: v for k, v in data['components'].items() if k not in ('url-shorten-memcached', 'media-memcached')}
edges = {k: np.sum(v['request'][360:] + v['response'][360:]) * 1e-6 for k, v in data['edges'].items()}
component2cpu = {k: v['cpu'][997] for k, v in components.items()}
exp = Experiment(path='experiments/story/cadvisor+istio.json')
perf = PerformanceEstimator(experiment_id='202207302259_202207310221')
cost = CostEstimator()


for r in range(1, len(components)):
    print('========================')
    print('r = %d / %d' % (r, len(components)))
    min_cloud, min_traffic = None, np.inf
    for onprem in itertools.combinations(components.keys(), r=r):
        cloud = {c for c in component2cpu if c not in onprem}
        if 'user-mongodb' not in onprem or \
                'post-storage-mongodb' not in onprem or \
                'media-mongodb' not in onprem or \
                sum(component2cpu[c] for c in onprem) > exp.config_onprem.LIMIT_CPU_CORE:
            continue

        traffic = 0
        for k, v in edges.items():
            if 'istio-ingressgateway' in k:
                continue
            if (k[0] in onprem) != (k[1] in onprem):
                traffic += v
        if traffic < min_traffic:
            min_traffic = traffic
            min_cloud = set(cloud)
    if min_cloud is not None:
        print('cloud   = {%s}' % ', '.join(['"'+c+'"' for c in min_cloud]))
        print('onprem  = {%s}' % ', '.join({c for c in component2cpu if c not in min_cloud}))

        print('Traffic = %.0f Mb' % min_traffic)
        print('   Cost = USD %.2f per day' % (cost.estimate(plan=PlacementPlan(exp=exp, mapping={
            component: [PlacementPlan.ONPREM, PlacementPlan.CLOUD][component in min_cloud] for component in exp.msvcs
        }))/7))
        results = perf.estimate(plan=min_cloud, detailed=False)
        print('   Perf = %.4fx' % results)
        results = perf.estimate(plan=min_cloud, detailed=True)
        for api in results:
            data = results[api]
            print('   > %s: %.2fms -> %.2f (%.1fx)' % (api,
                                                       np.mean([t[0] for t in data]),
                                                       np.mean([t[1] for t in data]),
                                                       np.mean([t[1] for t in data]) / np.mean([t[0] for t in data])))

# {user-mongodb, media-mongodb, post-storage-mongodb, write-home-timeline-rabbitmq, write-home-timeline-service, media-frontend}
# {user-mongodb, post-storage-mongodb, user-memcached, user-mention-service}