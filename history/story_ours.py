import itertools
from lib_cost import CostEstimator
from lib_performance import PerformanceEstimator
from core.application import PlacementPlan
from core.experiment import Experiment
import pickle
import numpy as np

with open('./experiments/story/telemetry.pkl', 'rb') as f:
    data = pickle.load(f)
timestamps = data['timestamps'][:120*4]
components = {k: v for k, v in data['components'].items() if k not in ('url-shorten-memcached', 'media-memcached')}
CPU_LIMIT = 4
edges = {k: (sum(v['request']) + sum(v['response'])) * 1e-6 for k, v in data['edges'].items()}
component2cpu = {k: v['cpu'][997] for k, v in components.items()}
exp = Experiment(path='experiments/story/cadvisor+istio.json')
perf = PerformanceEstimator(experiment_id='202207302259_202207310221')
cost = CostEstimator()


for r in range(1, len(components)):
    print('========================')
    print('r = %d / %d' % (r, len(components)))
    min_cloud, min_performance = None, np.inf
    for cloud in itertools.combinations(components.keys(), r=r):
        cloud = set(cloud)
        onprem = {c for c in component2cpu if c not in cloud}
        if 'user-mongodb' not in onprem or 'post-storage-mongodb' not in onprem or sum(component2cpu[c] for c in onprem) > CPU_LIMIT:
            continue
        performance = perf.estimate(cloud, detailed=False)
        if performance < min_performance:
            min_performance = performance
            min_cloud = cloud
    if min_cloud is not None:
        print('cloud   = {%s}' % ', '.join(min_cloud))
        print('onprem  = {%s}' % ', '.join({c for c in component2cpu if c not in min_cloud}))

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


{media-mongodb, media-frontend, post-storage-mongodb, user-mongodb, user-memcached, user-mention-service}
{media-mongodb, media-frontend, post-storage-mongodb, user-mongodb}