from core.application import Microservice
from datetime import datetime
from core.config import *
from core.lib_performance import PerformanceEstimator
from core.lib_cost import CostEstimator
from core.lib_availability import AvailabilityEstimator
from utils.data import DataLoader
import numpy as np
import json


class Experiment:
    def __init__(self, path, experiment_id, speedup_factor=144, ts_offset=1641024000, ignore=True):
        with open(path) as f:
            data = json.load(f)
        self.microservices = {k: Microservice(config=v) for k, v in data['components'].items()}
        if ignore:
            self.microservices = {k: v for k, v in self.microservices.items() if k not in {'url-shorten-memcached', 'media-memcached'}}
        self.msvcs = tuple(self.microservices.keys())
        self.step_size = data['step'] * speedup_factor
        self.timestamps = data['timestamps']
        self.timestamps_dt = [datetime.fromtimestamp(ts_offset + t * self.step_size) for t in range(len(self.timestamps))]
        self.now = 28 * 60 // 5
        self.config_onprem = OnPremConfig()
        self.config_cloud = CloudConfig()
        self.constraints = []
        self.performance_est = PerformanceEstimator(experiment_id=experiment_id)
        self.availability_est = AvailabilityEstimator()
        self.cost_est = CostEstimator()


def format_experiment(experiment, component2metrics):
    for component in component2metrics:
        for metric, ts in component2metrics[component]['utilization'].items():
            bb = list(ts[0][-60:])
            b = []
            for v in bb:
                b += [v, v]
            new_ts = b[-15:]
            for _ in range(7):
                new_ts += b
            new_ts += b[:34]
            new_ts = np.asarray(new_ts)

            if metric == 'cpu':
                new_ts = new_ts * DataLoader.UNIT / 1000
                experiment.microservices[component].cpu[experiment.now:] = new_ts
            elif metric == 'memory':
                new_ts = new_ts * DataLoader.UNIT / 1000
                experiment.microservices[component].memory[experiment.now:] = new_ts
            elif metric == 'usage':
                new_ts = new_ts * DataLoader.UNIT / 1000
                experiment.microservices[component].disk_usage[experiment.now:] = new_ts
    return experiment
