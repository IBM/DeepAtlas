from lib_performance import PerformanceEstimator
from constants import API2EDGES
from tqdm import tqdm
import numpy as np
import itertools


perf = PerformanceEstimator(experiment_id='202207302259_202207310221')

components = set()
for api, edges in API2EDGES.items():
    components = components.union(itertools.chain(*edges))
components = components.difference({'istio-ingressgateway'})

components = sorted(list(filter(lambda item: 'mongodb' not in item, components)))
apis = sorted(list(API2EDGES.keys()))

combinations = list(itertools.chain(*[list(itertools.combinations(components, r=r)) for r in range(1, len(components))]))

o = open('enumerate.csv', 'w')
o.write('score-mean,score-sum,%s,%s\n' % (','.join(apis), ','.join(components)))
for combination in tqdm(combinations):
    # print(combination)
    results = perf.estimate(plan=set(combination), detailed=True)

    x = []
    ratios = []
    for api in apis:
        before, after = zip(*results[api])
        ratio = round(np.mean(after) / np.mean(before), 4)
        x.append(ratio)
        ratios.append(ratio)
    for component in components:
        x.append(int(component in combination))
    x = [round(np.mean(ratios), 4), round(np.sum(ratios), 4)] + x
    o.write(','.join(map(str, x)) + '\n')

o.close()
