from core.experiment import Experiment
from core.recommender.random import RandomRecommender
from core.visualize import DashVis_v1
from core.moo import is_pareto
from lib_performance import PerformanceEstimator
from lib_cost import CostEstimator
from tqdm import tqdm
import numpy as np

performance_est = PerformanceEstimator(experiment_id='202207302259_202207310221')
cost_est = CostEstimator()
exp = Experiment(path='experiments/story/cadvisor+istio.json')
exp.constraints = ['user-mongodb', 'post-storage-mongodb', 'media-mongodb']

plans_random = RandomRecommender.run(exp, num_runs=10000)
costs = np.asarray([[performance_est.estimate(p), cost_est.estimate(p)] for p in tqdm(plans_random)])

I = is_pareto(costs)

xs, ys = [], []
for i in range(costs.shape[0]):
    if I[i]:
        print('cloud: %s' % str(plans_random[i].onprem_msvcs))
        xs.append(costs[i, 0])
        ys.append(costs[i, 1])
print('xs_baseline = %s' % str(xs))
print('ys_baseline = %s' % str(ys))

